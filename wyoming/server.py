import asyncio
import sys
from abc import ABC, abstractmethod
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Optional, Union
from urllib.parse import urlparse

from .event import (
    Event,
    async_get_stdin,
    async_read_event,
    async_read_event_from_bytes,
    async_write_event,
    event_to_bytes,
)

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment]


class AsyncEventTransport(ABC):
    """Reads and writes events over an underlying connection."""

    @abstractmethod
    async def read_event(self) -> Optional[Event]:
        """Read the next event, or None if the connection is closed."""

    @abstractmethod
    async def write_event(self, event: Event) -> None:
        """Write an event to the connection."""

    async def close(self) -> None:
        """Close the connection."""


class AsyncEventHandler(ABC):
    """Base class for async Wyoming event handler."""

    def __init__(self, transport: AsyncEventTransport) -> None:
        self._transport = transport
        self._is_running = False

    @abstractmethod
    async def handle_event(self, event: Event) -> bool:
        """Handle an event. Returning false will disconnect the client."""
        return True

    async def write_event(self, event: Event) -> None:
        """Send an event to the client."""
        await self._transport.write_event(event)

    async def run(self) -> None:
        """Receive events until stopped or handle_event returns false."""
        self._is_running = True

        try:
            while self._is_running:
                event = await self._transport.read_event()
                if event is None:
                    break

                if not (await self.handle_event(event)):
                    break
        finally:
            await self.disconnect()
            await self._transport.close()

    async def disconnect(self) -> None:
        """Called when client disconnects."""

    async def stop(self) -> None:
        """Try to stop the event handler."""
        self._is_running = False
        await self._transport.close()


HandlerFactory = Callable[[AsyncEventTransport], AsyncEventHandler]


class _StreamTransport(AsyncEventTransport):
    """Event transport over asyncio streams."""

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._reader = reader
        self._writer = writer

    async def read_event(self) -> Optional[Event]:
        return await async_read_event(self._reader)

    async def write_event(self, event: Event) -> None:
        await async_write_event(event, self._writer)

    async def close(self) -> None:
        self._writer.close()
        self._reader.feed_eof()


class _WebSocketTransport(AsyncEventTransport):
    """Event transport over a WebSocket connection."""

    def __init__(self, websocket) -> None:
        self._websocket = websocket

    async def read_event(self) -> Optional[Event]:
        try:
            message = await self._websocket.recv()
        except websockets.ConnectionClosed:
            return None

        return await async_read_event_from_bytes(message)

    async def write_event(self, event: Event) -> None:
        try:
            await self._websocket.send(event_to_bytes(event))
        except websockets.ConnectionClosed:
            pass

    async def close(self) -> None:
        await self._websocket.close()


class AsyncServer(ABC):
    """Base class for async Wyoming server."""

    def __init__(self) -> None:
        self._handlers: Dict[asyncio.Task, AsyncEventHandler] = {}

    @abstractmethod
    async def run(self, handler_factory: HandlerFactory) -> None:
        """Start server and block while running."""

    @staticmethod
    def from_uri(uri: str) -> "AsyncServer":
        """Create server from URI."""
        result = urlparse(uri)

        if result.scheme == "unix":
            return AsyncUnixServer(result.path)

        if result.scheme == "tcp":
            if (result.hostname is None) or (result.port is None):
                raise ValueError("A port must be specified when using a 'tcp://' URI")

            return AsyncTcpServer(result.hostname, result.port)

        if result.scheme == "stdio":
            return AsyncStdioServer()

        if result.scheme == "ws":
            if (result.hostname is None) or (result.port is None):
                raise ValueError("A port must be specified when using a 'ws://' URI")

            return AsyncWebSocketServer(result.hostname, result.port)

        raise ValueError(
            "Only 'stdio://', 'unix://', 'tcp://', or 'ws://' are supported"
        )

    async def _run_handler(
        self, handler_factory: HandlerFactory, transport: AsyncEventTransport
    ) -> None:
        handler = handler_factory(transport)
        task = asyncio.create_task(handler.run(), name="wyoming event handler")
        self._handlers[task] = handler
        task.add_done_callback(lambda t: self._handlers.pop(t, None))
        await task

    async def _run_stream_handler(
        self,
        handler_factory: HandlerFactory,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        await self._run_handler(handler_factory, _StreamTransport(reader, writer))

    async def start(self, handler_factory: HandlerFactory) -> None:
        """Start server without blocking."""

    async def stop(self) -> None:
        """Try to stop all event handlers."""
        await asyncio.gather(*(h.stop() for h in self._handlers.values()))


class AsyncStdioServer(AsyncServer):
    """Wyoming server over stdin/stdout."""

    async def run(self, handler_factory: HandlerFactory) -> None:
        """Start server and block while running."""
        reader = await async_get_stdin()

        # Get stdout writer.
        # NOTE: This will make print() non-blocking.
        loop = asyncio.get_running_loop()
        writer_transport, writer_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, loop)

        handler = handler_factory(_StreamTransport(reader, writer))
        await handler.run()


class AsyncTcpServer(AsyncServer):
    """Wyoming server over TCP."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self._server: Optional[asyncio.AbstractServer] = None

    async def run(self, handler_factory: HandlerFactory) -> None:
        handler_callback = partial(self._run_stream_handler, handler_factory)
        self._server = await asyncio.start_server(
            handler_callback, host=self.host, port=self.port
        )

        await self._server.serve_forever()

    async def start(self, handler_factory: HandlerFactory) -> None:
        """Start server without blocking."""
        handler_callback = partial(self._run_stream_handler, handler_factory)
        self._server = await asyncio.start_server(
            handler_callback, host=self.host, port=self.port
        )

        await self._server.start_serving()

    async def stop(self) -> None:
        """Try to stop all event handlers."""
        await super().stop()

        if self._server is not None:
            self._server.close()


class AsyncUnixServer(AsyncServer):
    """Wyoming server over a Unix domain socket."""

    def __init__(self, socket_path: Union[str, Path]) -> None:
        super().__init__()
        self.socket_path = Path(socket_path)
        self._server: Optional[asyncio.AbstractServer] = None

    async def run(self, handler_factory: HandlerFactory) -> None:
        """Start server and block while running."""
        # Need to unlink socket file if it exists
        self.socket_path.unlink(missing_ok=True)

        handler_callback = partial(self._run_stream_handler, handler_factory)
        self._server = await asyncio.start_unix_server(
            handler_callback, path=self.socket_path
        )

        try:
            await self._server.serve_forever()
        finally:
            # Unlink when we're done
            self.socket_path.unlink(missing_ok=True)

    async def start(self, handler_factory: HandlerFactory) -> None:
        """Start server without blocking."""
        # Need to unlink socket file if it exists
        self.socket_path.unlink(missing_ok=True)

        handler_callback = partial(self._run_stream_handler, handler_factory)
        self._server = await asyncio.start_unix_server(
            handler_callback, path=self.socket_path
        )

        await self._server.start_serving()

    async def stop(self) -> None:
        """Try to stop all event handlers."""
        await super().stop()

        if self._server is not None:
            self._server.close()

        self.socket_path.unlink(missing_ok=True)


class AsyncWebSocketServer(AsyncServer):
    """Wyoming server over WebSocket."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self._server: Optional["websockets.asyncio.server.Server"] = None

    async def run(self, handler_factory: HandlerFactory) -> None:
        """Start server and block while running."""
        if websockets is None:
            raise RuntimeError("websockets is required for 'ws://' support")

        self._server = await websockets.serve(
            partial(self._ws_callback, handler_factory),
            host=self.host,
            port=self.port,
        )

        await self._server.serve_forever()

    async def start(self, handler_factory: HandlerFactory) -> None:
        """Start server without blocking."""
        if websockets is None:
            raise RuntimeError("websockets is required for 'ws://' support")

        self._server = await websockets.serve(
            partial(self._ws_callback, handler_factory),
            host=self.host,
            port=self.port,
        )

        await self._server.start_serving()

    async def stop(self) -> None:
        """Try to stop all event handlers."""
        await super().stop()

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _ws_callback(self, handler_factory: HandlerFactory, websocket) -> None:
        await self._run_handler(handler_factory, _WebSocketTransport(websocket))
