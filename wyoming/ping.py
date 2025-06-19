"""Ping/pong messages."""

from dataclasses import dataclass
from typing import Optional

from .event import Event, Eventable

_PING_TYPE = "ping"
_PONG_TYPE = "pong"


@dataclass
class Ping(Eventable):
    """Request pong message."""

    text: Optional[str] = None
    """Text to copy to response."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _PING_TYPE

    def event(self) -> Event:
        return Event(
            type=_PING_TYPE,
            data={"text": self.text},
        )

    @staticmethod
    def from_event(event: Event) -> "Ping":
        return Ping(text=event.data.get("text"))


@dataclass
class Pong(Eventable):
    """Response to ping message."""

    text: Optional[str] = None
    """Text copied from request."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _PONG_TYPE

    def event(self) -> Event:
        return Event(
            type=_PONG_TYPE,
            data={"text": self.text},
        )

    @staticmethod
    def from_event(event: Event) -> "Pong":
        return Pong(text=event.data.get("text"))
