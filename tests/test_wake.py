"""Wake tests."""

import sys

from wyoming.wake import Detection, WakeProcessAsyncClient


async def test_wake_process_client_stops_when_program_exits() -> None:
    """A program that exits ends the stream instead of repeating detections."""
    async with WakeProcessAsyncClient(
        rate=16000,
        width=2,
        channels=1,
        program=sys.executable,
        program_args=["-c", "print('okay_nabu'); print()"],
    ) as client:
        event = await client.read_event()
        assert event is not None
        assert Detection.from_event(event).name == "okay_nabu"

        # Blank line is a detection without a name
        event = await client.read_event()
        assert event is not None
        assert Detection.from_event(event).name is None

        # Program exited
        assert await client.read_event() is None
