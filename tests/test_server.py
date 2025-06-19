"""Server tests."""

import asyncio
import socket
import tempfile
from pathlib import Path

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
