"""Audio output to speakers."""

import asyncio
import contextlib
import logging
from asyncio.subprocess import Process
from dataclasses import dataclass
from typing import List, Optional

from .audio import AudioChunk, AudioChunkConverter
from .client import AsyncClient
from .event import Event, Eventable

_LOGGER = logging.getLogger(__name__)

_PLAYED_TYPE = "played"


@dataclass
class Played(Eventable):
    """Audio has finished playing."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _PLAYED_TYPE

    def event(self) -> Event:
        return Event(type=_PLAYED_TYPE)

    @staticmethod
    def from_event(event: Event) -> "Played":
        return Played()


class SndProcessAsyncClient(AsyncClient, contextlib.AbstractAsyncContextManager):
    """Context manager for sending output audio to an external program."""

    def __init__(
        self,
        rate: int,
        width: int,
        channels: int,
        program: str,
        program_args: List[str],
    ) -> None:
        super().__init__()

        self.rate = rate
        self.width = width
        self.channels = channels
        self.program = program
        self.program_args = program_args

        self._proc: Optional[Process] = None
        self._chunk_converter = AudioChunkConverter(rate, width, channels)

    async def connect(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            self.program, *self.program_args, stdin=asyncio.subprocess.PIPE
        )

    async def disconnect(self) -> None:
        assert self._proc is not None
        assert self._proc.stdin is not None

        try:
            if self._proc.returncode is None:
                # Terminate process gracefully
                self._proc.stdin.close()
                await self._proc.wait()
        except ProcessLookupError:
            # Expected when process has already exited
            pass
        except Exception:
            _LOGGER.exception("Unexpected error stopping process: %s", self.program)
        finally:
            self._proc = None

    async def __aenter__(self) -> "SndProcessAsyncClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    async def read_event(self) -> Optional[Event]:
        """Client is write-only."""

    async def write_event(self, event: Event) -> None:
        assert self._proc is not None
        assert self._proc.stdin is not None

        if not AudioChunk.is_type(event.type):
            return

        chunk = AudioChunk.from_event(event)

        # Convert sample rate/width/channels if necessary
        chunk = self._chunk_converter.convert(chunk)

        self._proc.stdin.write(chunk.audio)
        await self._proc.stdin.drain()
