"""Test event reading/writing."""

import io
import json
from typing import Iterable

import pytest

from wyoming import __version__ as wyoming_version
from wyoming.event import (
    Event,
    async_read_event,
    async_write_event,
    read_event,
    write_event,
)

PAYLOAD = b"test\npayload"
DATA = {"test": "data"}
DATA_BYTES = json.dumps(DATA, ensure_ascii=False).encode("utf-8")


class FakeStreamWriter:
    def __init__(self) -> None:
        self._undrained_data = bytes()
        self._value = bytes()

    def write(self, data: bytes) -> None:
        self._undrained_data += data

    def writelines(self, data: Iterable[bytes]) -> None:
        for line in data:
            self.write(line)

    async def drain(self) -> None:
        self._value += self._undrained_data
        self._undrained_data = bytes()

    def getvalue(self) -> bytes:
        return self._value


class FakeStreamReader:
    def __init__(self, value: bytes) -> None:
        self._value_io = io.BytesIO(value)

    async def readline(self) -> bytes:
        return self._value_io.readline()

    async def readexactly(self, n: int) -> bytes:
        data = self._value_io.read(n)
        assert len(data) == n
        return data


# -----------------------------------------------------------------------------


def test_write_event() -> None:
    """Test synchronous event writing."""
    event = Event(type="test-event", data=DATA, payload=PAYLOAD)
    with io.BytesIO() as buf:
        write_event(event, buf)
        buf.seek(0)
        event_bytes = buf.getvalue()

    with io.BytesIO(event_bytes) as reader:
        # First line is JSON with event type and data/payload lengths.
        #
        # A "data" field may also be present here, but it should be short to
        # avoid overflowing a line buffer.
        assert json.loads(reader.readline()) == {
            "type": event.type,
            "version": wyoming_version,
            "data_length": len(DATA_BYTES),
            "payload_length": len(PAYLOAD),
        }

        # Data dict comes next, encoded as UTF-8 JSON.
        # It should be merged on top of the "data" field, if present.
        assert reader.read(len(DATA_BYTES)) == DATA_BYTES

        # Payload comes last
        assert reader.read(len(PAYLOAD)) == PAYLOAD

        # No more data
        assert reader.read(1) == b""


@pytest.mark.asyncio
async def test_async_write_event() -> None:
    """Test asynchronous event writing."""
    event = Event(type="test-event", data=DATA, payload=PAYLOAD)
    writer = FakeStreamWriter()
    await async_write_event(event, writer)  # type: ignore
    event_bytes = writer.getvalue()

    with io.BytesIO(event_bytes) as reader:
        # First line is JSON with event type and data/payload lengths.
        #
        # A "data" field may also be present here, but it should be short to
        # avoid overflowing a line buffer.
        assert json.loads(reader.readline()) == {
            "type": event.type,
            "version": wyoming_version,
            "data_length": len(DATA_BYTES),
            "payload_length": len(PAYLOAD),
        }

        # Data dict comes next, encoded as UTF-8 JSON.
        # It should be merged on top of the "data" field, if present.
        assert reader.read(len(DATA_BYTES)) == DATA_BYTES

        # Payload comes last
        assert reader.read(len(PAYLOAD)) == PAYLOAD

        # No more data
        assert reader.read(1) == b""


def test_write_event_no_payload() -> None:
    """Test synchronous event writing without a payload."""
    event = Event(type="test-event", data=DATA, payload=None)
    with io.BytesIO() as buf:
        write_event(event, buf)
        buf.seek(0)
        event_bytes = buf.getvalue()

    with io.BytesIO(event_bytes) as reader:
        assert json.loads(reader.readline()) == {
            "type": event.type,
            "version": wyoming_version,
            "data_length": len(DATA_BYTES),
        }

        assert reader.read(len(DATA_BYTES)) == DATA_BYTES

        # No payload
        assert reader.read(1) == b""


@pytest.mark.asyncio
async def test_async_write_event_no_payload() -> None:
    """Test asynchronous event writing without a payload."""
    event = Event(type="test-event", data=DATA, payload=None)
    writer = FakeStreamWriter()
    await async_write_event(event, writer)  # type: ignore
    event_bytes = writer.getvalue()

    with io.BytesIO(event_bytes) as reader:
        assert json.loads(reader.readline()) == {
            "type": event.type,
            "version": wyoming_version,
            "data_length": len(DATA_BYTES),
        }

        assert reader.read(len(DATA_BYTES)) == DATA_BYTES

        # No payload
        assert reader.read(1) == b""


def test_read_event() -> None:
    """Test synchronous event reading."""
    header = {
        "type": "test-event",
        "version": wyoming_version,
        "data_length": len(DATA_BYTES),
        "payload_length": len(PAYLOAD),
        # inline data
        "data": {
            "test": "this will be overwritten by DATA",
            "test2": "this will not",
        },
    }

    with io.BytesIO() as buf:
        # First line is JSON with event type and data/payload lengths.
        header_bytes = json.dumps(header, ensure_ascii=False).encode("utf-8")
        buf.write(header_bytes)
        buf.write(b"\n")

        # Data dict comes next, encoded as UTF-8 JSON.
        buf.write(DATA_BYTES)

        # Payload comes last
        buf.write(PAYLOAD)

        buf.seek(0)
        event_bytes = buf.getvalue()

    with io.BytesIO(event_bytes) as reader:
        event = read_event(reader)
        assert event == Event(
            type="test-event",
            # inline data was overwritten
            data={"test": "data", "test2": "this will not"},
            payload=PAYLOAD,
        )


def test_read_event_no_data() -> None:
    """Test synchronous event reading with no data."""
    header = {"type": "test-event", "version": wyoming_version}

    with io.BytesIO() as buf:
        header_bytes = json.dumps(header, ensure_ascii=False).encode("utf-8")
        buf.write(header_bytes)
        buf.write(b"\n")
        buf.seek(0)
        event_bytes = buf.getvalue()

    with io.BytesIO(event_bytes) as reader:
        event = read_event(reader)
        assert event == Event(type="test-event")


@pytest.mark.asyncio
async def test_async_read_event() -> None:
    """Test asynchronous event reading."""
    header = {
        "type": "test-event",
        "version": wyoming_version,
        "data_length": len(DATA_BYTES),
        "payload_length": len(PAYLOAD),
        # inline data
        "data": {
            "test": "this will be overwritten by DATA",
            "test2": "this will not",
        },
    }

    with io.BytesIO() as buf:
        # First line is JSON with event type and data/payload lengths.
        header_bytes = json.dumps(header, ensure_ascii=False).encode("utf-8")
        buf.write(header_bytes)
        buf.write(b"\n")

        # Data dict comes next, encoded as UTF-8 JSON.
        buf.write(DATA_BYTES)

        # Payload comes last
        buf.write(PAYLOAD)

        buf.seek(0)
        event_bytes = buf.getvalue()

    reader = FakeStreamReader(event_bytes)
    event = await async_read_event(reader)  # type: ignore
    assert event == Event(
        type="test-event",
        # inline data was overwritten
        data={"test": "data", "test2": "this will not"},
        payload=PAYLOAD,
    )


@pytest.mark.asyncio
async def test_async_read_event_no_data() -> None:
    """Test asynchronous event reading with no data."""
    header = {"type": "test-event", "version": wyoming_version}

    with io.BytesIO() as buf:
        header_bytes = json.dumps(header, ensure_ascii=False).encode("utf-8")
        buf.write(header_bytes)
        buf.write(b"\n")
        buf.seek(0)
        event_bytes = buf.getvalue()

    reader = FakeStreamReader(event_bytes)
    event = await async_read_event(reader)  # type: ignore
    assert event == Event(type="test-event")
