"""Text to speech."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .event import Event, Eventable

DOMAIN = "tts"
_SYNTHESIZE_TYPE = "synthesize"

# streaming
_SYNTHESIZE_START_TYPE = "synthesize-start"
_SYNTHESIZE_CHUNK_TYPE = "synthesize-chunk"
_SYNTHESIZE_STOP_TYPE = "synthesize-stop"
_SYNTHESIZE_STOPPED_TYPE = "synthesize-stopped"


@dataclass
class SynthesizeVoice:
    """Information about the desired voice for synthesis."""

    name: Optional[str] = None
    """Voice name from tts info (overrides language)."""

    language: Optional[str] = None
    """Voice language from tts info."""

    speaker: Optional[str] = None
    """Voice speaker from tts info."""

    def to_dict(self) -> Dict[str, str]:
        if self.name is not None:
            voice = {"name": self.name}
            if self.speaker is not None:
                voice["speaker"] = self.speaker
        elif self.language is not None:
            voice = {"language": self.language}
        else:
            voice = {}

        return voice

    @staticmethod
    def from_dict(voice: Dict[str, Any]) -> "Optional[SynthesizeVoice]":
        if "name" in voice:
            return SynthesizeVoice(
                name=voice["name"],
                speaker=voice.get("speaker"),
            )

        if "language" in voice:
            return SynthesizeVoice(name=voice["language"])

        return None


@dataclass
class Synthesize(Eventable):
    """Request to synthesize audio from text."""

    text: str
    """Text to synthesize."""

    voice: Optional[SynthesizeVoice] = None
    """Voice to use during synthesis."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _SYNTHESIZE_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {"text": self.text}
        if self.voice is not None:
            data["voice"] = self.voice.to_dict()
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_SYNTHESIZE_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Synthesize":
        return Synthesize(
            text=event.data["text"],
            voice=SynthesizeVoice.from_dict(event.data.get("voice", {})),
            context=event.data.get("context"),
        )


@dataclass
class SynthesizeStart(Eventable):
    """Start of streaming request to synthesize audio from text."""

    voice: Optional[SynthesizeVoice] = None
    """Voice to use during synthesis."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _SYNTHESIZE_START_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.voice is not None:
            data["voice"] = self.voice.to_dict()
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_SYNTHESIZE_START_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "SynthesizeStart":
        return SynthesizeStart(
            voice=SynthesizeVoice.from_dict(event.data.get("voice", {})),
            context=event.data.get("context"),
        )


@dataclass
class SynthesizeChunk(Eventable):
    """Text chunk from streaming request to synthesize audio from text."""

    text: str
    """Chunk of text to synthesize."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _SYNTHESIZE_CHUNK_TYPE

    def event(self) -> Event:
        return Event(type=_SYNTHESIZE_CHUNK_TYPE, data={"text": self.text})

    @staticmethod
    def from_event(event: Event) -> "SynthesizeChunk":
        return SynthesizeChunk(text=event.data["text"])


@dataclass
class SynthesizeStop(Eventable):
    """End of streaming request to synthesize audio from text."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _SYNTHESIZE_STOP_TYPE

    def event(self) -> Event:
        return Event(type=_SYNTHESIZE_STOP_TYPE)

    @staticmethod
    def from_event(event: Event) -> "SynthesizeStop":
        return SynthesizeStop()


@dataclass
class SynthesizeStopped(Eventable):
    """End of streaming response to streaming request."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _SYNTHESIZE_STOPPED_TYPE

    def event(self) -> Event:
        return Event(type=_SYNTHESIZE_STOPPED_TYPE)

    @staticmethod
    def from_event(event: Event) -> "SynthesizeStopped":
        return SynthesizeStopped()
