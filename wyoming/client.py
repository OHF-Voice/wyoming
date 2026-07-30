import asyncio
from abc import ABC
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

from .event import (
    Event,
    async_get_stdin,
    async_get_stdout,
    async_read_event,
    async_read_event_from_bytes,
    async_write_event,
    event_to_bytes,
)

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment]


class AsyncClient(ABC):
    """Base class for Wyoming async client."""

    def __init__(self) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def read_event(self) -> Optional[Event]:
        assert self._reader is not None
        return await async_read_event(self._reader)

    async def write_event(self, event: Event) -> None:
        assert self._writer is not None
        await async_write_event(event, self._writer)

    async def connect(self) -> None:
        pass

    async def __aenter__(self):
        await self.connect()
        return self

    async def disconnect(self) -> None:
        pass

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.disconnect()

    @staticmethod
    def from_uri(uri: str) -> "AsyncClient":
        result = urlparse(uri)

        if result.scheme == "unix":
            return AsyncUnixClient(result.path)

        if result.scheme == "tcp":
            if (result.hostname is None) or (result.port is None):
                raise ValueError("A port must be specified when using a 'tcp://' URI")

            return AsyncTcpClient(result.hostname, result.port)

        if result.scheme == "stdio":
            return AsyncStdioClient()

        if result.scheme == "ws" or result.scheme == "wss":
            return AsyncWebSocketClient(uri)

        raise ValueError(
            "Only 'stdio://', 'unix://', 'tcp://', or 'ws://' are supported"
        )


class AsyncTcpClient(AsyncClient):
    """TCP Wyoming client."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()

        self.host = host
        self.port = port

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(
            host=self.host,
            port=self.port,
        )

    async def disconnect(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None

        if writer is not None:
            writer.close()
            await writer.wait_closed()


class AsyncUnixClient(AsyncClient):
    """Unix domain socket Wyoming client."""

    def __init__(self, socket_path: Union[str, Path]) -> None:
        super().__init__()

        self.socket_path = Path(socket_path)

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_unix_connection(
            path=self.socket_path
        )

    async def disconnect(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None

        if writer is not None:
            writer.close()
            await writer.wait_closed()


class AsyncStdioClient(AsyncClient):
    """Standard output Wyoming client."""

    def __init__(self) -> None:
        super().__init__()

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def read_event(self) -> Optional[Event]:
        if self._reader is None:
            self._reader = await async_get_stdin()

        assert self._reader is not None
        return await async_read_event(self._reader)

    async def write_event(self, event: Event) -> None:
        if self._writer is None:
            self._writer = await async_get_stdout()

        assert self._writer is not None
        await async_write_event(event, self._writer)


class AsyncWebSocketClient(AsyncClient):
    """WebSocket Wyoming client."""

    def __init__(self, uri: str) -> None:
        super().__init__()

        self.uri = uri
        self._websocket = None

    async def connect(self) -> None:
        if websockets is None:
            raise RuntimeError("websockets is required for 'ws://' support")

        self._websocket = await websockets.connect(
            self.uri,
        )

    async def disconnect(self) -> None:
        websocket = self._websocket
        self._websocket = None

        if websocket is not None:
            await websocket.close()

    async def read_event(self) -> Optional[Event]:
        assert self._websocket is not None

        try:
            message = await self._websocket.recv()
        except websockets.ConnectionClosed:
            return None

        return await async_read_event_from_bytes(message)

    async def write_event(self, event: Event) -> None:
        assert self._websocket is not None

        try:
            await self._websocket.send(event_to_bytes(event))
        except websockets.ConnectionClosed:
            pass
