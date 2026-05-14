"""User-defined events."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .event import Event, Eventable

_USER_EVENT_TYPE = "user-event"


@dataclass
class UserEvent(Eventable):
    """User-defined event."""

    name: str
    """Name of user event type."""

    data: Optional[Dict[str, Any]] = None
    """User event data."""

    context: Optional[Dict[str, Any]] = None
    """Context from previous interactions."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _USER_EVENT_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {"name": self.name}
        if self.data is not None:
            data["data"] = self.data
        if self.context is not None:
            data["context"] = self.context
        return Event(type=_USER_EVENT_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "UserEvent":
        return UserEvent(
            name=event.data["name"],
            data=event.data.get("data"),
            context=event.data.get("context"),
        )
