"""Server tests."""

import asyncio
import logging
import socket
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest

from wyoming.client import AsyncClient
from wyoming.event import Event
from wyoming.ping import Ping, Pong
from wyoming.server import (
    AsyncEventHandler,
    AsyncServer,
    AsyncStdioServer,
    AsyncTcpServer,
    AsyncUnixServer,
)


class PingHandler(AsyncEventHandler):
    async def handle_event(self, event: Event) -> bool:
        if Ping.is_type(event.type):
            ping = Ping.from_event(event)
            await self.write_event(Pong(text=ping.text).event())
            return False

        return True


def test_from_uri() -> None:
    """Test AsyncServer.from_uri"""
    # Bad scheme
    with pytest.raises(ValueError):
        AsyncServer.from_uri("ftp://127.0.0.1:5000")

    # Missing hostname
    with pytest.raises(ValueError):
        AsyncServer.from_uri("tcp://:5000")

    # Missing port
    with pytest.raises(ValueError):
        AsyncServer.from_uri("tcp://127.0.0.1")

    stdio_server = AsyncServer.from_uri("stdio://")
    assert isinstance(stdio_server, AsyncStdioServer)

    tcp_server = AsyncServer.from_uri("tcp://127.0.0.1:5000")
    assert isinstance(tcp_server, AsyncTcpServer)
    assert tcp_server.host == "127.0.0.1"
    assert tcp_server.port == 5000

    unix_server = AsyncServer.from_uri("unix:///path/to/socket")
    assert isinstance(unix_server, AsyncUnixServer)
    assert unix_server.socket_path == Path("/path/to/socket")


@pytest.mark.asyncio
async def test_unix_server() -> None:
    """Test sending events to and from a Unix socket server."""
    with tempfile.TemporaryDirectory() as temp_dir:
        socket_path = Path(temp_dir) / "test.socket"
        uri = f"unix://{socket_path}"
        unix_server = AsyncServer.from_uri(uri)
        await unix_server.start(PingHandler)

        # Wait for path to exist
        while not socket_path.exists():
            await asyncio.sleep(0.1)

        client = AsyncClient.from_uri(uri)
        await client.connect()
        await client.write_event(Ping(text="test").event())

        event = await asyncio.wait_for(client.read_event(), timeout=1)
        assert event is not None
        assert Pong.is_type(event.type)
        assert Pong.from_event(event).text == "test"

        await client.disconnect()
        await unix_server.stop()


@pytest.mark.asyncio
async def test_tcp_server() -> None:
    """Test sending events to and from a TCP server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    port = sock.getsockname()[1]
    sock.close()

    uri = f"tcp://127.0.0.1:{port}"

    tcp_server = AsyncServer.from_uri(uri)
    await tcp_server.start(PingHandler)

    # Wait for socket to open
    for _ in range(10):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            break
        except ConnectionRefusedError:
            await asyncio.sleep(0.1)

    client = AsyncClient.from_uri(uri)
    await client.connect()
    await client.write_event(Ping(text="test").event())

    event = await asyncio.wait_for(client.read_event(), timeout=1)
    assert event is not None
    assert Pong.is_type(event.type)
    assert Pong.from_event(event).text == "test"

    await client.disconnect()
    await tcp_server.stop()


class DisconnectAwareHandler(AsyncEventHandler):
    """Handler that records the exception raised by write_event on disconnect."""

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        super().__init__(reader, writer)
        self.write_error: Optional[BaseException] = None

    async def handle_event(self, event: Event) -> bool:
        # Repeatedly write until the client disconnects so we hit drain().
        try:
            while True:
                await self.write_event(Pong(text="x" * 4096).event())
                await asyncio.sleep(0)
        except BaseException as err:
            self.write_error = err
            raise


@pytest.mark.asyncio
async def test_client_disconnect_propagates_to_handler(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A client disconnect mid-write should surface to handle_event and not
    leave an unretrieved task exception or emit an error log."""
    handlers: List[DisconnectAwareHandler] = []

    def factory(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> DisconnectAwareHandler:
        handler = DisconnectAwareHandler(reader, writer)
        handlers.append(handler)
        return handler

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    port = sock.getsockname()[1]
    sock.close()

    uri = f"tcp://127.0.0.1:{port}"
    tcp_server = AsyncServer.from_uri(uri)
    await tcp_server.start(factory)

    client = AsyncClient.from_uri(uri)
    for _ in range(10):
        try:
            await client.connect()
            break
        except ConnectionRefusedError:
            await asyncio.sleep(0.1)
    await client.write_event(Ping(text="trigger").event())

    # Wait for at least one Pong so we know the server has entered the
    # write loop in handle_event before we abort the connection.
    pong = await asyncio.wait_for(client.read_event(), timeout=2)
    assert pong is not None and Pong.is_type(pong.type)

    # Capture the server task before severing the connection.
    server_tasks = list(tcp_server._handlers)
    assert server_tasks, "Server never created a handler task"
    server_task = server_tasks[0]

    # Hard-close the client to provoke a write failure on the server side.
    assert client._writer is not None
    client._writer.transport.abort()
    await client.disconnect()

    # Wait for the server task to complete, then let _handler_done run.
    await asyncio.wait({server_task}, timeout=2)
    assert server_task.done(), "Server task did not complete in time"
    await asyncio.sleep(0)

    # The write_event call inside handle_event should have raised so
    # handle_event can react to the disconnect.
    assert handlers, "Handler was never instantiated"
    handler = handlers[0]
    assert handler.write_error is not None
    assert isinstance(handler.write_error, ConnectionError)

    # No "Unhandled exception" log should have been emitted for a normal
    # client disconnect.
    unhandled = [
        record
        for record in caplog.get_records("call")
        if record.levelno >= logging.ERROR
        and "Unhandled exception" in record.getMessage()
    ]
    assert not unhandled, unhandled

    await tcp_server.stop()


@pytest.mark.asyncio
async def test_handler_done_silences_incomplete_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """asyncio.IncompleteReadError surfaces when a client disconnects
    mid-readexactly. _handler_done must treat it as an expected disconnect
    and not log it as 'Unhandled exception'."""

    class _ReadingHandler(AsyncEventHandler):
        async def handle_event(self, event: Event) -> bool:
            return True

    tcp_server = AsyncTcpServer("127.0.0.1", 0)

    # Simulate a completed handler task that raised IncompleteReadError,
    # exercising _handler_done in isolation.
    async def raises_incomplete_read() -> None:
        raise asyncio.IncompleteReadError(partial=b"", expected=1)

    task = asyncio.create_task(raises_incomplete_read())
    tcp_server._handlers[task] = _ReadingHandler(  # type: ignore[arg-type]
        asyncio.StreamReader(), None  # type: ignore[arg-type]
    )
    task.add_done_callback(tcp_server._handler_done)

    with pytest.raises(asyncio.IncompleteReadError):
        await task
    await asyncio.sleep(0)  # let done-callback run

    unhandled = [
        record
        for record in caplog.get_records("call")
        if record.levelno >= logging.ERROR
        and "Unhandled exception" in record.getMessage()
    ]
    assert not unhandled, unhandled
    assert task not in tcp_server._handlers
