"""Test audio utilities."""

import io
import wave

from wyoming.audio import AudioChunk, AudioChunkConverter, wav_to_chunks


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
