"""Error event."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .event import Event, Eventable

_ERROR_TYPE = "error"


@dataclass
class Error(Eventable):
    """Error with text and an optional code."""

    text: str
    """Human-readable error message."""

    code: Optional[str] = None
    """Machine-readable error code."""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _ERROR_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {"text": self.text}
        if self.code is not None:
            data["code"] = self.code

        return Event(type=_ERROR_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "Error":
        return Error(text=event.data["text"], code=event.data.get("code"))
