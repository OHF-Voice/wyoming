"""Intent recognition and handling."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .event import Event, Eventable

DOMAIN = "handle"
_HANDLED_TYPE = "handled"
_NOT_HANDLED_TYPE = "not-handled"
_HANDLED_START_TYPE = "handled-start"
_HANDLED_CHUNK_TYPE = "handled-chunk"
_HANDLED_STOP_TYPE = "handled-stop"


@dataclass
class Handled(Eventable):
    """Result of successful intent handling."""

    text: Optional[str] = None
    """Human-readable response."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _HANDLED_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.text is not None:
            data["text"] = self.text
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_HANDLED_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Handled":
        if not event.data:
            return Handled()

        return Handled(text=event.data.get("text"), context=event.data.get("context"))


@dataclass
class NotHandled(Eventable):
    """Result of intent handling failure."""

    text: Optional[str] = None
    """Human-readable response."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _NOT_HANDLED_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.text is not None:
            data["text"] = self.text
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_NOT_HANDLED_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "NotHandled":
        if not event.data:
            return NotHandled()

        return NotHandled(
            text=event.data.get("text"), context=event.data.get("context")
        )


@dataclass
class HandledStart(Eventable):
    """Start of streaming result of successful intent handling."""

    context: Optional[Dict[str, Any]] = None
    """Context for next interaction."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _HANDLED_START_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {}
        if self.context is not None:
            data["context"] = self.context

        return Event(type=_HANDLED_START_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "HandledStart":
        if not event.data:
            return HandledStart()

        return HandledStart(context=event.data.get("context"))


@dataclass
class HandledChunk(Eventable):
    """Response chunk of streaming result of successful intent handling."""

    text: str
    """Chunk of response text."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _HANDLED_CHUNK_TYPE

    def event(self) -> Event:
        return Event(type=_HANDLED_CHUNK_TYPE, data={"text": self.text})

    @staticmethod
    def from_event(event: Event) -> "HandledChunk":
        return HandledChunk(text=event.data["text"])


@dataclass
class HandledStop(Eventable):
    """End of streaming sesult of successful intent handling."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _HANDLED_STOP_TYPE

    def event(self) -> Event:
        return Event(type=_HANDLED_STOP_TYPE)

    @staticmethod
    def from_event(event: Event) -> "HandledStop":
        return HandledStop()
