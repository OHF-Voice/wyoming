"""Wake word detection"""

import asyncio
import contextlib
import logging
from asyncio.subprocess import Process
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .audio import AudioChunk, AudioChunkConverter
from .client import AsyncClient
from .event import Event, Eventable

_LOGGER = logging.getLogger(__name__)

DOMAIN = "wake"
_DETECTION_TYPE = "detection"
_DETECT_TYPE = "detect"
_NOT_DETECTED_TYPE = "not-detected"


@dataclass
class Detection(Eventable):
    """Wake word was detected."""

    name: Optional[str] = None
    """Name of model."""

    timestamp: Optional[int] = None
    """Timestamp of audio chunk with detection"""

    speaker: Optional[str] = None
    """Name of speaker."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _DETECTION_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {
            "name": self.name,
            "timestamp": self.timestamp,
            "speaker": self.speaker,
        }
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_DETECTION_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Detection":
        data = event.data or {}
        return Detection(
            name=data.get("name"),
            timestamp=data.get("timestamp"),
            speaker=data.get("speaker"),
            context=data.get("context"),
        )


@dataclass
class Detect(Eventable):
    """Wake word detection request.

    Followed by AudioStart, AudioChunk+, AudioStop
    """

    names: Optional[List[str]] = None
    """Names of models to detect (None = any)."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _DETECT_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {"names": self.names}
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_DETECT_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Detect":
        data = event.data or {}
        return Detect(names=data.get("names"), context=data.get("context"))


@dataclass
class NotDetected(Eventable):
    """Audio stream ended before wake word was detected."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _NOT_DETECTED_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_NOT_DETECTED_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "NotDetected":
        if not event.data:
            return NotDetected()

        return NotDetected(context=event.data.get("context"))


class WakeProcessAsyncClient(AsyncClient, contextlib.AbstractAsyncContextManager):
    """Context manager for doing wake word detection with an external program."""

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
            self.program,
            *self.program_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
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

    async def __aenter__(self) -> "WakeProcessAsyncClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    async def read_event(self) -> Optional[Event]:
        assert self._proc is not None
        assert self._proc.stdout is not None

        line = (await self._proc.stdout.readline()).decode("utf-8").strip()
        name = line if line else None
        return Detection(name=name).event()

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
