"""Microphone tests."""

import sys
import time

from wyoming.audio import AudioChunk
from wyoming.mic import MicProcessAsyncClient


async def test_mic_process_client_timestamp_milliseconds() -> None:
    """Chunk timestamps are in milliseconds, like the rest of the protocol."""
    async with MicProcessAsyncClient(
        rate=16000,
        width=2,
        channels=1,
        samples_per_chunk=2,
        program=sys.executable,
        program_args=["-c", "import sys; sys.stdout.buffer.write(bytes(4))"],
    ) as client:
        before_ms = time.monotonic_ns() // 1_000_000
        event = await client.read_event()
        after_ms = time.monotonic_ns() // 1_000_000

    assert event is not None
    chunk = AudioChunk.from_event(event)
    assert chunk.audio == bytes(4)
    assert chunk.timestamp is not None
    assert before_ms <= chunk.timestamp <= after_ms
