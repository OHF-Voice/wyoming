"""Information about available services, models, etc.."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .audio import AudioFormat
from .event import Event, Eventable
from .util.dataclasses_json import DataClassJsonMixin

DOMAIN = "info"
_DESCRIBE_TYPE = "describe"
_INFO_TYPE = "info"


@dataclass
class Describe(Eventable):
    """Request info message."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _DESCRIBE_TYPE

    def event(self) -> Event:
        return Event(type=_DESCRIBE_TYPE)

    @staticmethod
    def from_event(event: Event) -> "Describe":
        return Describe()


@dataclass
class Attribution(DataClassJsonMixin):
    """Attribution for an artifact."""

    name: str
    """Who made it."""

    url: str
    """Where it's from."""


@dataclass
class Artifact(DataClassJsonMixin):
    """Information about a service, model, etc.."""

    name: str
    """Name/id of artifact."""

    attribution: Attribution
    """Who made the artifact and where it's from."""

    installed: bool
    """True if the artifact is currently installed."""

    description: Optional[str]
    """Human-readable description of the artifact."""

    version: Optional[str]
    """Version of the artifact."""


# -----------------------------------------------------------------------------


@dataclass
class AsrModel(Artifact):
    """Speech-to-text model."""

    languages: List[str]
    """List of supported model languages."""


@dataclass
class AsrProgram(Artifact):
    """Speech-to-text service."""

    models: List[AsrModel]
    """List of available models."""

    supports_transcript_streaming: bool = False
    """True if transcript streaming events are supported."""


# -----------------------------------------------------------------------------


@dataclass
class TtsVoiceSpeaker(DataClassJsonMixin):
    """Individual speaker in a multi-speaker voice."""

    name: str
    """Name/id of speaker."""


@dataclass
class TtsVoice(Artifact):
    """Text-to-speech voice."""

    languages: List[str]
    """List of languages available in the voice."""

    speakers: Optional[List[TtsVoiceSpeaker]] = None
    """List of individual speakers in the voice."""


@dataclass
class TtsProgram(Artifact):
    """Text-to-speech service."""

    voices: List[TtsVoice]
    """List of available voices."""

    supports_synthesize_streaming: bool = False
    """True if synthesize text streaming events are supported."""


# -----------------------------------------------------------------------------


@dataclass
class HandleModel(Artifact):
    """Intent handling model."""

    languages: List[str]
    """List of supported languages in the model."""


@dataclass
class HandleProgram(Artifact):
    """Intent handling service."""

    models: List[HandleModel]
    """List of available models."""

    supports_handled_streaming: bool = False
    """True if handled response streaming events are supported."""


# -----------------------------------------------------------------------------


@dataclass
class WakeModel(Artifact):
    """Wake word detection model."""

    languages: List[str]
    """List of languages supported by the model."""

    phrase: Optional[str]
    """Wake up phrase used by the model."""


@dataclass
class WakeProgram(Artifact):
    """Wake word detection service."""

    models: List[WakeModel]
    """List of available models."""


# -----------------------------------------------------------------------------


@dataclass
class IntentModel(Artifact):
    """Intent recognition model."""

    languages: List[str]
    """List of languages supported by the model."""


@dataclass
class IntentProgram(Artifact):
    """Intent recognition service."""

    models: List[IntentModel]
    """List of available models."""


# -----------------------------------------------------------------------------


@dataclass
class Satellite(Artifact):
    """Satellite information."""

    area: Optional[str] = None
    """Name of the area the satellite is in."""

    has_vad: Optional[bool] = None
    """True if a local VAD will be used to detect the end of voice commands."""

    active_wake_words: Optional[List[str]] = None
    """Wake words that are currently being listened for."""

    max_active_wake_words: Optional[int] = None
    """Maximum number of local wake words that can be run simultaneously."""

    supports_trigger: Optional[bool] = None
    """Satellite supports remotely triggering pipeline runs."""


# -----------------------------------------------------------------------------


@dataclass
class MicProgram(Artifact):
    """Microphone information."""

    mic_format: AudioFormat
    """Input audio format."""


# -----------------------------------------------------------------------------


@dataclass
class SndProgram(Artifact):
    """Sound output information."""

    snd_format: AudioFormat
    """Output audio format."""


# -----------------------------------------------------------------------------


@dataclass
class Info(Eventable):
    """Response to describe message with information about available services, models, etc."""

    asr: List[AsrProgram] = field(default_factory=list)
    """Speech-to-text services."""

    tts: List[TtsProgram] = field(default_factory=list)
    """Text-to-speech services."""

    handle: List[HandleProgram] = field(default_factory=list)
    """Intent handling services."""

    intent: List[IntentProgram] = field(default_factory=list)
    """Intent recognition services."""

    wake: List[WakeProgram] = field(default_factory=list)
    """Wake word detection services."""

    mic: List[MicProgram] = field(default_factory=list)
    """Audio input services."""

    snd: List[SndProgram] = field(default_factory=list)
    """Audio output services."""

    satellite: Optional[Satellite] = None
    """Satellite information."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _INFO_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {
            "asr": [p.to_dict() for p in self.asr],
            "tts": [p.to_dict() for p in self.tts],
            "handle": [p.to_dict() for p in self.handle],
            "intent": [p.to_dict() for p in self.intent],
            "wake": [p.to_dict() for p in self.wake],
            "mic": [p.to_dict() for p in self.mic],
            "snd": [p.to_dict() for p in self.snd],
        }

        if self.satellite is not None:
            data["satellite"] = self.satellite.to_dict()

        return Event(type=_INFO_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Info":
        satellite: Optional[Satellite] = None
        satellite_data = event.data.get("satellite")
        if satellite_data is not None:
            satellite = Satellite.from_dict(satellite_data)

        return Info(
            asr=[AsrProgram.from_dict(d) for d in event.data.get("asr", [])],
            tts=[TtsProgram.from_dict(d) for d in event.data.get("tts", [])],
            handle=[HandleProgram.from_dict(d) for d in event.data.get("handle", [])],
            intent=[IntentProgram.from_dict(d) for d in event.data.get("intent", [])],
            wake=[WakeProgram.from_dict(d) for d in event.data.get("wake", [])],
            mic=[MicProgram.from_dict(d) for d in event.data.get("mic", [])],
            snd=[SndProgram.from_dict(d) for d in event.data.get("snd", [])],
            satellite=satellite,
        )
