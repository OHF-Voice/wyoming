import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Optional, Union
from urllib.parse import urlparse

from .event import Event, async_get_stdin, async_read_event, async_write_event

_LOGGER = logging.getLogger(__name__)


class AsyncEventHandler(ABC):
    """Base class for async Wyoming event handler."""

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.reader = reader
        self.writer = writer
        self._is_running = False

    @abstractmethod
    async def handle_event(self, event: Event) -> bool:
        """Handle an event. Returning false will disconnect the client."""
        return True

    async def write_event(self, event: Event) -> None:
        """Send an event to the client."""
        await async_write_event(event, self.writer)

    async def run(self) -> None:
        """Receive events until stopped or handle_event returns false."""
        self._is_running = True

        try:
            while self._is_running:
                event = await async_read_event(self.reader)
                if event is None:
                    break

                if not (await self.handle_event(event)):
                    break
        finally:
            await self.disconnect()

    async def disconnect(self) -> None:
        """Called when client disconnects."""

    async def stop(self) -> None:
        """Try to stop the event handler."""
        self._is_running = False
        self.writer.close()
        self.reader.feed_eof()


HandlerFactory = Callable[
    [asyncio.StreamReader, asyncio.StreamWriter], AsyncEventHandler
]


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

        raise ValueError("Only 'stdio://', 'unix://', or 'tcp://' are supported")

    async def _handler_callback(
        self,
        handler_factory: HandlerFactory,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        handler = handler_factory(reader, writer)
        task = asyncio.create_task(handler.run(), name="wyoming event handler")
        self._handlers[task] = handler
        task.add_done_callback(self._handler_done)

    def _handler_done(self, task: asyncio.Task) -> None:
        self._handlers.pop(task, None)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is None or isinstance(
            exc, (ConnectionError, asyncio.IncompleteReadError)
        ):
            return
        _LOGGER.exception("Unhandled exception in Wyoming event handler", exc_info=exc)

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

        handler = handler_factory(reader, writer)
        while True:
            event = await async_read_event(reader)
            if event is None:
                break

            if not (await handler.handle_event(event)):
                break


class AsyncTcpServer(AsyncServer):
    """Wyoming server over TCP."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self._server: Optional[asyncio.AbstractServer] = None

    async def run(self, handler_factory: HandlerFactory) -> None:
        handler_callback = partial(self._handler_callback, handler_factory)
        self._server = await asyncio.start_server(
            handler_callback, host=self.host, port=self.port
        )

        await self._server.serve_forever()

    async def start(self, handler_factory: HandlerFactory) -> None:
        """Start server without blocking."""
        handler_callback = partial(self._handler_callback, handler_factory)
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

        handler_callback = partial(self._handler_callback, handler_factory)
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

        handler_callback = partial(self._handler_callback, handler_factory)
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
