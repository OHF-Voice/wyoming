import asyncio
import json
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Dict, Iterable, Optional

from .version import __version__

_TYPE = "type"
_DATA = "data"
_DATA_LENGTH = "data_length"
_PAYLOAD_LENGTH = "payload_length"
_NEWLINE = "\n".encode()
_VERSION = "version"
_VERSION_NUMBER = __version__


@dataclass
class Event:
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    payload: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {_TYPE: self.type, _DATA: self.data}

    @staticmethod
    def from_dict(event_dict: Dict[str, Any]) -> "Event":
        return Event(type=event_dict["type"], data=event_dict.get("data", {}))


class Eventable(ABC):
    @abstractmethod
    def event(self) -> Event:
        pass

    @staticmethod
    @abstractmethod
    def is_type(event_type: str) -> bool:
        pass

    def to_dict(self) -> Dict[str, Any]:
        return self.event().data

    @staticmethod
    @abstractmethod
    def from_event(event: Event) -> "Eventable":
        pass


async def async_get_stdin(
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> asyncio.StreamReader:
    """Get StreamReader for stdin."""
    if loop is None:
        loop = asyncio.get_running_loop()

    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader), sys.stdin
    )

    return reader


async def async_get_stdout(
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> asyncio.StreamWriter:
    """Get StreamWriter for stdout."""
    if loop is None:
        loop = asyncio.get_running_loop()

    writer_transport, writer_protocol = await loop.connect_write_pipe(
        lambda: asyncio.streams.FlowControlMixin(loop=loop),
        os.fdopen(sys.stdout.fileno(), "wb"),
    )
    return asyncio.streams.StreamWriter(writer_transport, writer_protocol, None, loop)


async def async_read_event(reader: asyncio.StreamReader) -> Optional[Event]:
    try:
        json_line = await reader.readline()
        if not json_line:
            return None

        event_dict = json.loads(json_line)
        data_length = event_dict.get(_DATA_LENGTH)
        if (data_length is not None) and (data_length > 0):
            # Merge data
            data_bytes = await reader.readexactly(data_length)
            data_dict = event_dict.get(_DATA, {})
            data_dict.update(json.loads(data_bytes))
            event_dict[_DATA] = data_dict

        payload_length = event_dict.get(_PAYLOAD_LENGTH)

        payload: Optional[bytes] = None
        if (payload_length is not None) and (payload_length > 0):
            payload = await reader.readexactly(payload_length)

        return Event(
            type=event_dict[_TYPE], data=event_dict.get(_DATA, {}), payload=payload
        )
    except (KeyboardInterrupt, ValueError):
        pass

    return None


async def async_write_event(event: Event, writer: asyncio.StreamWriter):
    event_dict: Dict[str, Any] = event.to_dict()
    event_dict[_VERSION] = _VERSION_NUMBER

    data_dict = event_dict.pop(_DATA, None)
    data_bytes: Optional[bytes] = None
    if data_dict:
        data_bytes = json.dumps(data_dict, ensure_ascii=False).encode("utf-8")
        event_dict[_DATA_LENGTH] = len(data_bytes)

    if event.payload:
        event_dict[_PAYLOAD_LENGTH] = len(event.payload)

    json_line = json.dumps(event_dict, ensure_ascii=False)

    try:
        writer.writelines((json_line.encode(), _NEWLINE))

        if data_bytes:
            writer.write(data_bytes)

        if event.payload:
            writer.write(event.payload)

        await writer.drain()
    except KeyboardInterrupt:
        pass


async def async_write_events(events: Iterable[Event], writer: asyncio.StreamWriter):
    try:
        await asyncio.gather(*(async_write_event(event, writer) for event in events))
    except KeyboardInterrupt:
        pass


def read_event(reader: Optional[BinaryIO] = None) -> Optional[Event]:
    if reader is None:
        reader = sys.stdin.buffer

    try:
        json_line = reader.readline()

        if not json_line:
            return None

        event_dict = json.loads(json_line)
        data_length = event_dict.get(_DATA_LENGTH)
        if (data_length is not None) and (data_length > 0):
            # Merge data
            data_bytes = reader.read(data_length)
            while len(data_bytes) < data_length:
                data_bytes += reader.read(data_length - len(data_bytes))

            data_dict = event_dict.get(_DATA, {})
            data_dict.update(json.loads(data_bytes))
            event_dict[_DATA] = data_dict

        payload_length = event_dict.get(_PAYLOAD_LENGTH)

        payload: Optional[bytes] = None
        if payload_length is not None:
            payload = reader.read(payload_length)
            while len(payload) < payload_length:
                payload += reader.read(payload_length - len(payload))

        return Event(
            type=event_dict[_TYPE], data=event_dict.get(_DATA, {}), payload=payload
        )
    except (KeyboardInterrupt, ValueError):
        pass

    return None


def write_event(event: Event, writer: Optional[BinaryIO] = None):
    if writer is None:
        writer = sys.stdout.buffer

    event_dict: Dict[str, Any] = event.to_dict()
    event_dict[_VERSION] = _VERSION_NUMBER

    data_dict = event_dict.pop(_DATA, None)
    data_bytes: Optional[bytes] = None
    if data_dict:
        data_bytes = json.dumps(data_dict, ensure_ascii=False).encode("utf-8")
        event_dict[_DATA_LENGTH] = len(data_bytes)

    if event.payload:
        event_dict[_PAYLOAD_LENGTH] = len(event.payload)

    json_line = json.dumps(event_dict, ensure_ascii=False)

    try:
        writer.writelines((json_line.encode(), _NEWLINE))

        if data_bytes:
            writer.write(data_bytes)

        if event.payload:
            writer.write(event.payload)

        writer.flush()
    except KeyboardInterrupt:
        pass
