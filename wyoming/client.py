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
    async_write_event,
)


class AsyncClient(ABC):
    """Base class for Wyoming async client."""

    def __init__(
        self,
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
    ) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

        # Seconds to wait when connecting, or None to wait indefinitely
        self.connect_timeout = connect_timeout

        # Seconds to wait for each event, or None to wait indefinitely
        self.read_timeout = read_timeout

    async def read_event(self) -> Optional[Event]:
        assert self._reader is not None

        if self.read_timeout is None:
            return await async_read_event(self._reader)

        return await asyncio.wait_for(
            async_read_event(self._reader), timeout=self.read_timeout
        )

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
    def from_uri(
        uri: str,
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
    ) -> "AsyncClient":
        result = urlparse(uri)
        timeouts = {"connect_timeout": connect_timeout, "read_timeout": read_timeout}

        if result.scheme == "unix":
            return AsyncUnixClient(result.path, **timeouts)

        if result.scheme == "tcp":
            if (result.hostname is None) or (result.port is None):
                raise ValueError("A port must be specified when using a 'tcp://' URI")

            return AsyncTcpClient(result.hostname, result.port, **timeouts)

        if result.scheme == "stdio":
            return AsyncStdioClient(**timeouts)

        raise ValueError("Only 'stdio://', 'unix://', or 'tcp://' are supported")


class AsyncTcpClient(AsyncClient):
    """TCP Wyoming client."""

    def __init__(
        self,
        host: str,
        port: int,
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
    ) -> None:
        super().__init__(connect_timeout=connect_timeout, read_timeout=read_timeout)

        self.host = host
        self.port = port

    async def connect(self) -> None:
        connect = asyncio.open_connection(host=self.host, port=self.port)

        if self.connect_timeout is not None:
            connect = asyncio.wait_for(connect, timeout=self.connect_timeout)

        self._reader, self._writer = await connect

    async def disconnect(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None

        if writer is not None:
            writer.close()
            await writer.wait_closed()


class AsyncUnixClient(AsyncClient):
    """Unix domain socket Wyoming client."""

    def __init__(
        self,
        socket_path: Union[str, Path],
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
    ) -> None:
        super().__init__(connect_timeout=connect_timeout, read_timeout=read_timeout)

        self.socket_path = Path(socket_path)

    async def connect(self) -> None:
        connect = asyncio.open_unix_connection(path=self.socket_path)

        if self.connect_timeout is not None:
            connect = asyncio.wait_for(connect, timeout=self.connect_timeout)

        self._reader, self._writer = await connect

    async def disconnect(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None

        if writer is not None:
            writer.close()
            await writer.wait_closed()


class AsyncStdioClient(AsyncClient):
    """Standard output Wyoming client."""

    async def read_event(self) -> Optional[Event]:
        if self._reader is None:
            self._reader = await async_get_stdin()

        return await super().read_event()

    async def write_event(self, event: Event) -> None:
        if self._writer is None:
            self._writer = await async_get_stdout()

        await super().write_event(event)
