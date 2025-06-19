"""Microphone input."""

import asyncio
import contextlib
import logging
import time
from asyncio.subprocess import Process
from typing import List, Optional

from .audio import AudioChunk
from .client import AsyncClient
from .event import Event

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mic"


class MicProcessAsyncClient(AsyncClient, contextlib.AbstractAsyncContextManager):
    """Context manager for getting microphone audio from an external program."""

    def __init__(
        self,
        rate: int,
        width: int,
        channels: int,
        samples_per_chunk: int,
        program: str,
        program_args: List[str],
    ) -> None:
        super().__init__()

        self.rate = rate
        self.width = width
        self.channels = channels
        self.samples_per_chunk = samples_per_chunk
        self.bytes_per_chunk = samples_per_chunk * width * channels
        self.program = program
        self.program_args = program_args

        self._proc: Optional[Process] = None

    async def connect(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            self.program, *self.program_args, stdout=asyncio.subprocess.PIPE
        )

    async def disconnect(self) -> None:
        assert self._proc is not None

        try:
            if self._proc.returncode is None:
                # Terminate process gracefully
                self._proc.terminate()
                await self._proc.wait()
        except ProcessLookupError:
            # Expected when process has already exited
            pass
        except Exception:
            _LOGGER.exception("Unexpected error stopping process: %s", self.program)
        finally:
            self._proc = None

    async def __aenter__(self) -> "MicProcessAsyncClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    async def read_event(self) -> Optional[Event]:
        assert self._proc is not None
        assert self._proc.stdout is not None

        try:
            audio_bytes = await self._proc.stdout.readexactly(self.bytes_per_chunk)
            return AudioChunk(
                rate=self.rate,
                width=self.width,
                channels=self.channels,
                audio=audio_bytes,
                timestamp=time.monotonic_ns(),
            ).event()
        except asyncio.IncompleteReadError:
            return None

    async def write_event(self, event: Event) -> None:
        """Client is read-only."""
