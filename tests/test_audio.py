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
