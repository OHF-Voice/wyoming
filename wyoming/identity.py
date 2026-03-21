"""Identity recognition."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .event import Event, Eventable

DOMAIN = "identity"
_IDENTIFY_TYPE = "identify"
_IDENTIFIED_TYPE = "identified"
_NOT_IDENTIFIED_TYPE = "not-identified"


@dataclass
class Identify(Eventable):
    """Request to identify an identity from an audio stream.

    Followed by AudioStart, AudioChunk+, AudioStop
    """

    name: Optional[str] = None
    """Name of identity recognition model to use."""

    names: Optional[List[str]] = None
    """Names of identities to consider (None = any)."""

    context: Optional[Dict[str, Any]] = None
    """Context from previous interactions."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _IDENTIFY_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.name is not None:
            data["name"] = self.name
        if self.names is not None:
            data["names"] = self.names
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_IDENTIFY_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Identify":
        data = event.data or {}
        return Identify(
            name=data.get("name"),
            names=data.get("names"),
            context=data.get("context"),
        )


@dataclass
class Identified(Eventable):
    """Identity was recognized."""

    name: str
    """Name/id of identified identity."""

    confidence: Optional[float] = None
    """Confidence score of the identification."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _IDENTIFIED_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {"name": self.name}
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_IDENTIFIED_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Identified":
        return Identified(
            name=event.data["name"],
            confidence=event.data.get("confidence"),
            context=event.data.get("context"),
        )


@dataclass
class NotIdentified(Eventable):
    """Audio stream ended before an identity could be recognized."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _NOT_IDENTIFIED_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_NOT_IDENTIFIED_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "NotIdentified":
        if not event.data:
            return NotIdentified()

        return NotIdentified(context=event.data.get("context"))
