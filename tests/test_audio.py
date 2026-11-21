"""Test audio utilities."""

import io
import random
import wave

from wyoming.audio import (
    AudioChunk,
    AudioChunkConverter,
    AudioStart,
    AudioStop,
    wav_to_chunks,
)


def test_chunk_converter() -> None:
    """Test audio chunk converter."""
    converter = AudioChunkConverter(rate=16000, width=2, channels=1)
    input_chunk = AudioChunk(
        rate=48000,
        width=4,
        channels=2,
        audio=bytes(1 * 48000 * 4 * 2),  # 1 sec
    )

    output_chunk = converter.convert(input_chunk)
    assert output_chunk.rate == 16000
    assert output_chunk.width == 2
    assert output_chunk.channels == 1
    assert len(output_chunk.audio) == 1 * 16000 * 2 * 1  # 1 sec


def test_chunk_converter_8bit() -> None:
    """Test conversion to/from unsigned 8-bit audio.

    WAV 8-bit samples are unsigned (silence = 128), unlike wider samples which
    are signed (silence = 0). The converter must account for this.
    """
    # Unsigned 8-bit: silence, max, min, and a positive value
    audio_8bit = bytes([128, 255, 0, 192])

    # 8-bit -> 16-bit: silence must map to 0, not full-scale noise
    to_16bit = AudioChunkConverter(width=2)
    chunk_16bit = to_16bit.convert(
        AudioChunk(rate=16000, width=1, channels=1, audio=audio_8bit)
    )
    assert chunk_16bit.width == 2
    samples_16bit = [
        int.from_bytes(chunk_16bit.audio[i : i + 2], "little", signed=True)
        for i in range(0, len(chunk_16bit.audio), 2)
    ]
    assert samples_16bit[0] == 0  # unsigned silence -> signed silence

    # 16-bit -> 8-bit round-trips back to the original unsigned bytes
    to_8bit = AudioChunkConverter(width=1)
    chunk_8bit = to_8bit.convert(chunk_16bit)
    assert chunk_8bit.width == 1
    assert chunk_8bit.audio == audio_8bit


def test_wav_to_chunks() -> None:
    """Test WAV file to audio chunks."""
    with io.BytesIO() as wav_io:
        wav_write: wave.Wave_write = wave.open(wav_io, "wb")
        with wav_write:
            wav_write.setframerate(16000)
            wav_write.setsampwidth(2)
            wav_write.setnchannels(1)
            wav_write.writeframes(bytes(1 * 16000 * 2 * 1))  # 1 sec

        wav_io.seek(0)
        wav_bytes = wav_io.getvalue()

    with io.BytesIO(wav_bytes) as wav_io:
        wav_read: wave.Wave_read = wave.open(wav_io, "rb")
        chunks = list(wav_to_chunks(wav_read, samples_per_chunk=1000))
        assert len(chunks) == 16
        for chunk in chunks:
            assert isinstance(chunk, AudioChunk)
            assert chunk.rate == 16000
            assert chunk.width == 2
            assert chunk.channels == 1
            assert len(chunk.audio) == 1000 * 2  # 1000 samples


def _wav_bytes(rate: int, num_samples: int) -> bytes:
    with io.BytesIO() as wav_io:
        wav_write: wave.Wave_write = wave.open(wav_io, "wb")
        with wav_write:
            wav_write.setframerate(rate)
            wav_write.setsampwidth(2)
            wav_write.setnchannels(1)
            wav_write.writeframes(bytes(num_samples * 2))

        return wav_io.getvalue()


def test_wav_to_chunks_start_timestamp() -> None:
    """Test that the start event uses the timestamp argument."""
    with io.BytesIO(_wav_bytes(16000, 16000)) as wav_io:
        wav_read: wave.Wave_read = wave.open(wav_io, "rb")
        events = list(
            wav_to_chunks(
                wav_read, samples_per_chunk=1000, timestamp=5000, start_event=True
            )
        )

    assert isinstance(events[0], AudioStart)
    assert events[0].timestamp == 5000
    assert isinstance(events[1], AudioChunk)
    assert events[1].timestamp == 5000


def test_wav_to_chunks_timestamps_do_not_drift() -> None:
    """Test that chunk timestamps do not lose milliseconds at every chunk."""
    # 1024 samples at 22050 Hz is 46.44 ms, not a whole number of milliseconds
    with io.BytesIO(_wav_bytes(22050, 22050)) as wav_io:  # 1 sec
        wav_read: wave.Wave_read = wave.open(wav_io, "rb")
        events = list(wav_to_chunks(wav_read, samples_per_chunk=1024, stop_event=True))

    chunks = [event for event in events if isinstance(event, AudioChunk)]
    assert chunks[-1].timestamp == (21 * 1024 * 1000) // 22050

    assert isinstance(events[-1], AudioStop)
    assert events[-1].timestamp == 1000


def test_chunk_converter_stereo_to_mono_averages() -> None:
    """Stereo to mono averages the channels instead of summing them."""
    left, right = 20000, 10000
    stereo = left.to_bytes(2, "little", signed=True) + right.to_bytes(
        2, "little", signed=True
    )

    converter = AudioChunkConverter(channels=1)
    mono_chunk = converter.convert(
        AudioChunk(rate=16000, width=2, channels=2, audio=stereo * 10)
    )

    assert mono_chunk.channels == 1
    assert len(mono_chunk.audio) == 10 * 2
    samples = [
        int.from_bytes(mono_chunk.audio[i : i + 2], "little", signed=True)
        for i in range(0, len(mono_chunk.audio), 2)
    ]
    assert samples == [(left + right) // 2] * 10


def test_chunk_converter_multichannel_to_mono_averages() -> None:
    """More than two channels are averaged per frame, not read as stereo pairs."""
    for channels in (3, 4, 6):
        values = [1000 * (c + 1) for c in range(channels)]
        frame = b"".join(v.to_bytes(2, "little", signed=True) for v in values)

        mono_chunk = AudioChunkConverter(channels=1).convert(
            AudioChunk(rate=16000, width=2, channels=channels, audio=frame * 10)
        )

        assert mono_chunk.channels == 1
        assert len(mono_chunk.audio) == 10 * 2
        samples = [
            int.from_bytes(mono_chunk.audio[i : i + 2], "little", signed=True)
            for i in range(0, len(mono_chunk.audio), 2)
        ]
        assert samples == [sum(values) // channels] * 10


def test_chunk_converter_multichannel_to_stereo() -> None:
    """More than two channels become stereo with one frame per input frame."""
    frame = b"".join(v.to_bytes(2, "little", signed=True) for v in (100, 200, 300, 400))

    stereo_chunk = AudioChunkConverter(channels=2).convert(
        AudioChunk(rate=16000, width=2, channels=4, audio=frame * 10)
    )

    assert stereo_chunk.channels == 2
    assert stereo_chunk.audio == (250).to_bytes(2, "little", signed=True) * 2 * 10


def _reference_downmix(audio: bytes, width: int, channels: int) -> bytes:
    """Sample-by-sample average of each frame's channels (unsigned at width 1)."""
    signed = width > 1
    frame_size = width * channels
    mono = bytearray()
    for frame_start in range(0, len(audio) - frame_size + 1, frame_size):
        total = sum(
            int.from_bytes(audio[i : i + width], "little", signed=signed)
            for i in range(frame_start, frame_start + frame_size, width)
        )
        mono += (total // channels).to_bytes(width, "little", signed=signed)

    return bytes(mono)


def test_chunk_converter_multichannel_widths() -> None:
    """Downmix matches a per-sample average for every width, including extremes."""
    rng = random.Random(1234)
    for width in (1, 2, 3, 4):
        bits = 8 * width
        if width == 1:
            low, high = 0, 255
        else:
            low, high = -(2 ** (bits - 1)), 2 ** (bits - 1) - 1

        for channels in (3, 4, 6):
            values = [low] * channels + [high] * channels
            values += [rng.randint(low, high) for _ in range(channels * 50)]
            audio = b"".join(
                v.to_bytes(width, "little", signed=width > 1) for v in values
            )

            # Trailing partial frame is dropped
            audio += b"\x01" * (width * (channels - 1))

            mono_chunk = AudioChunkConverter(channels=1).convert(
                AudioChunk(rate=16000, width=width, channels=channels, audio=audio)
            )

            assert mono_chunk.width == width
            assert len(mono_chunk.audio) == 52 * width
            assert mono_chunk.audio == _reference_downmix(audio, width, channels)


def test_chunk_converter_multichannel_unsigned_silence() -> None:
    """8-bit audio is unsigned, so silence (128) stays silence."""
    mono_chunk = AudioChunkConverter(channels=1).convert(
        AudioChunk(rate=16000, width=1, channels=4, audio=bytes([128]) * 4 * 10)
    )

    assert mono_chunk.audio == bytes([128]) * 10


def test_chunk_converter_8bit_stereo_to_mono() -> None:
    """Unsigned 8-bit stereo is averaged around 128, not as signed bytes."""
    mono_chunk = AudioChunkConverter(channels=1).convert(
        AudioChunk(rate=16000, width=1, channels=2, audio=bytes([255, 1, 200, 100]))
    )

    assert mono_chunk.audio == bytes([128, 150])


def test_chunk_converter_8bit_resample_matches_16bit() -> None:
    """Resampling unsigned 8-bit audio near silence (128) does not wrap around."""
    values = list(range(121, 138))
    audio_8bit = bytes(values)
    audio_16bit = b"".join(
        ((v - 128) << 8).to_bytes(2, "little", signed=True) for v in values
    )

    chunk_8bit = AudioChunkConverter(rate=12000).convert(
        AudioChunk(rate=16000, width=1, channels=1, audio=audio_8bit)
    )
    chunk_16bit = AudioChunkConverter(rate=12000, width=1).convert(
        AudioChunk(rate=16000, width=2, channels=1, audio=audio_16bit)
    )

    assert chunk_8bit.audio == chunk_16bit.audio
    assert all(abs(sample - 128) <= 10 for sample in chunk_8bit.audio)
