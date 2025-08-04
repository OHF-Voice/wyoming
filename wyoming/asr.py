"""Speech to text."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .event import Event, Eventable

DOMAIN = "asr"
_TRANSCRIPT_TYPE = "transcript"
_TRANSCRIBE_TYPE = "transcribe"
_TRANSCRIPT_START_TYPE = "transcript-start"
_TRANSCRIPT_CHUNK_TYPE = "transcript-chunk"
_TRANSCRIPT_STOP_TYPE = "transcript-stop"


@dataclass
class Transcript(Eventable):
    """Transcription response from ASR system"""

    text: str
    """Text transcription of spoken audio"""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    language: Optional[str] = None
    """Language of the text."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _TRANSCRIPT_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {"text": self.text}
        if self.language is not None:
            data["language"] = self.language

        if self.context is not None:
            data["context"] = self.context

        return Event(type=_TRANSCRIPT_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Transcript":
        return Transcript(
            text=event.data["text"],
            language=event.data.get("language"),
            context=event.data.get("context"),
        )


@dataclass
class Transcribe(Eventable):
    """Transcription request to ASR system.

    Followed by AudioStart, AudioChunk+, AudioStop
    """

    name: Optional[str] = None
    """Name of ASR model to use"""

    language: Optional[str] = None
    """Language of spoken audio to follow"""

    context: Optional[Dict[str, Any]] = None
    """Context from previous interactions."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _TRANSCRIBE_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.name is not None:
            data["name"] = self.name

        if self.language is not None:
            data["language"] = self.language

        if self.context is not None:
            data["context"] = self.context

        return Event(type=_TRANSCRIBE_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Transcribe":
        data = event.data or {}
        return Transcribe(
            name=data.get("name"),
            language=data.get("language"),
            context=data.get("context"),
        )


@dataclass
class TranscriptStart(Eventable):
    """Streaming transcription response from ASR system"""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    language: Optional[str] = None
    """Language of the text."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _TRANSCRIPT_START_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.language is not None:
            data["language"] = self.language
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_TRANSCRIPT_START_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "TranscriptStart":
        if not event.data:
            return TranscriptStart()

        return TranscriptStart(
            context=event.data.get("context"), language=event.data.get("language")
        )


@dataclass
class TranscriptChunk(Eventable):
    """Chunk of streaming transcription response from ASR system"""

    text: str
    """Chunk of transcript text."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _TRANSCRIPT_CHUNK_TYPE

    def event(self) -> Event:
        return Event(type=_TRANSCRIPT_CHUNK_TYPE, data={"text": self.text})

    @staticmethod
    def from_event(event: Event) -> "TranscriptChunk":
        return TranscriptChunk(text=event.data["text"])


@dataclass
class TranscriptStop(Eventable):
    """End of streaming transcription response from ASR system"""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _TRANSCRIPT_STOP_TYPE

    def event(self) -> Event:
        return Event(type=_TRANSCRIPT_STOP_TYPE)

    @staticmethod
    def from_event(event: Event) -> "TranscriptStop":
        return TranscriptStop()
