"""Audio input/output."""

import argparse
import array
import io
import sys
import wave
from dataclasses import dataclass
from typing import Iterable, Optional, Union

try:
    # Use built-in audioop until it's removed in Python 3.13
    import audioop  # pylint: disable=deprecated-module
except ImportError:
    from . import pyaudioop as audioop  # type: ignore[no-redef]

from .event import Event, Eventable
from .util.dataclasses_json import DataClassJsonMixin

_CHUNK_TYPE = "audio-chunk"
_START_TYPE = "audio-start"
_STOP_TYPE = "audio-stop"


@dataclass
class AudioFormat(DataClassJsonMixin):
    """Base class for events with audio format information."""

    rate: int
    """Hertz"""

    width: int
    """Bytes"""

    channels: int
    """Mono = 1"""


@dataclass
class AudioChunk(AudioFormat, Eventable):
    """Chunk of raw PCM audio."""

    audio: bytes
    """Raw audio"""

    timestamp: Optional[int] = None
    """Milliseconds"""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _CHUNK_TYPE

    def event(self) -> Event:
        return Event(
            type=_CHUNK_TYPE,
            data={
                "rate": self.rate,
                "width": self.width,
                "channels": self.channels,
                "timestamp": self.timestamp,
            },
            payload=self.audio,
        )

    @staticmethod
    def from_event(event: Event) -> "AudioChunk":
        return AudioChunk(
            rate=event.data["rate"],
            width=event.data["width"],
            channels=event.data["channels"],
            audio=event.payload or bytes(),
            timestamp=event.data.get("timestamp"),
        )

    @property
    def samples(self) -> int:
        return len(self.audio) // (self.width * self.channels)

    @property
    def seconds(self) -> float:
        return self.samples / self.rate

    @property
    def milliseconds(self) -> int:
        return int(self.seconds * 1_000)


@dataclass
class AudioStart(AudioFormat, Eventable):
    """Audio stream has started."""

    timestamp: Optional[int] = None
    """Milliseconds"""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _START_TYPE

    def event(self) -> Event:
        return Event(
            type=_START_TYPE,
            data={
                "rate": self.rate,
                "width": self.width,
                "channels": self.channels,
                "timestamp": self.timestamp,
            },
        )

    @staticmethod
    def from_event(event: Event) -> "AudioStart":
        return AudioStart(
            rate=event.data["rate"],
            width=event.data["width"],
            channels=event.data["channels"],
            timestamp=event.data.get("timestamp"),
        )


@dataclass
class AudioStop(Eventable):
    """Audio stream has stopped."""

    timestamp: Optional[int] = None
    """Milliseconds"""

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _STOP_TYPE

    def event(self) -> Event:
        return Event(
            type=_STOP_TYPE,
            data={"timestamp": self.timestamp},
        )

    @staticmethod
    def from_event(event: Event) -> "AudioStop":
        return AudioStop(timestamp=event.data.get("timestamp"))


@dataclass
class AudioChunkConverter:
    """Converts audio chunks using audioop/pyaudioop."""

    rate: Optional[int] = None
    width: Optional[int] = None
    channels: Optional[int] = None
    _ratecv_state = None

    def convert(self, chunk: AudioChunk) -> AudioChunk:
        """Converts sample rate, width, and channels as necessary."""
        if (
            ((self.rate is None) or (chunk.rate == self.rate))
            and ((self.width is None) or (chunk.width == self.width))
            and ((self.channels is None) or (chunk.channels == self.channels))
        ):
            return chunk

        audio_bytes = chunk.audio
        width = chunk.width

        if width == 1:
            # 8-bit samples are unsigned, but audioop expects signed samples
            audio_bytes = audioop.bias(audio_bytes, 1, -128)

        if (self.width is not None) and (chunk.width != self.width):
            # Convert sample width
            audio_bytes = audioop.lin2lin(audio_bytes, chunk.width, self.width)
            width = self.width

        channels = chunk.channels
        if (self.channels is not None) and (chunk.channels != self.channels):
            # Convert to mono or stereo
            if channels > 2:
                # audioop only mixes stereo, so average the channels to mono first
                audio_bytes = _average_channels(audio_bytes, width, channels)
                channels = 1

            if self.channels == 1:
                if channels == 2:
                    audio_bytes = audioop.tomono(audio_bytes, width, 0.5, 0.5)
            elif self.channels == 2:
                audio_bytes = audioop.tostereo(audio_bytes, width, 1.0, 1.0)
            else:
                raise ValueError(f"Cannot convert to channels: {self.channels}")

            channels = self.channels

        rate = chunk.rate
        if (self.rate is not None) and (chunk.rate != self.rate):
            # Resample
            audio_bytes, self._ratecv_state = audioop.ratecv(
                audio_bytes,
                width,
                channels,
                chunk.rate,
                self.rate,
                self._ratecv_state,
            )
            rate = self.rate

        if width == 1:
            audio_bytes = audioop.bias(audio_bytes, 1, 128)

        return AudioChunk(
            rate,
            width,
            channels,
            audio_bytes,
            timestamp=chunk.timestamp,
        )


_ARRAY_TYPECODES = {1: "b", 2: "h", 4: "i"}


def _average_channels(audio: bytes, width: int, channels: int) -> bytes:
    """Average each frame's channels into one sample.

    Samples are signed and little-endian. A trailing partial frame is dropped.
    """
    frame_size = width * channels
    audio = audio[: len(audio) - (len(audio) % frame_size)]

    if width == 3:
        # No 24-bit array type: widen to 32-bit by adding a zero low byte
        # (value << 8), average, and drop the low byte again (>> 8). Flooring
        # commutes with the shift, so this matches averaging the 24-bit values.
        wide = bytearray(len(audio) // 3 * 4)
        for byte in range(3):
            wide[byte + 1 :: 4] = audio[byte::3]

        mono_wide = _average_channels(bytes(wide), 4, channels)
        narrow = bytearray(len(mono_wide) // 4 * 3)
        for byte in range(3):
            narrow[byte::3] = mono_wide[byte + 1 :: 4]

        return bytes(narrow)

    typecode = _ARRAY_TYPECODES.get(width)
    if typecode is None:
        raise ValueError(f"Unsupported sample width: {width}")

    samples = array.array(typecode)
    if samples.itemsize != width:
        raise ValueError(f"No {width}-byte array type on this platform")

    samples.frombytes(audio)
    if sys.byteorder == "big":
        samples.byteswap()

    columns = [samples[c::channels] for c in range(channels)]
    mono = array.array(
        typecode, [total // channels for total in map(sum, zip(*columns))]
    )
    if sys.byteorder == "big":
        mono.byteswap()

    return mono.tobytes()


def wav_to_chunks(
    wav_file: wave.Wave_read,
    samples_per_chunk: int,
    timestamp: int = 0,
    start_event: bool = False,
    stop_event: bool = False,
) -> Iterable[Union[AudioStart, AudioChunk, AudioStop]]:
    """Splits WAV file into AudioChunks."""
    rate = wav_file.getframerate()
    width = wav_file.getsampwidth()
    channels = wav_file.getnchannels()

    if start_event:
        yield AudioStart(rate=rate, width=width, channels=channels, timestamp=timestamp)

    # Count samples so rounding each chunk to whole milliseconds doesn't add up
    samples = 0
    audio_bytes = wav_file.readframes(samples_per_chunk)
    while audio_bytes:
        chunk = AudioChunk(
            rate=rate,
            width=width,
            channels=channels,
            audio=audio_bytes,
            timestamp=timestamp + (samples * 1_000) // rate,
        )
        yield chunk
        samples += chunk.samples
        audio_bytes = wav_file.readframes(samples_per_chunk)

    if stop_event:
        yield AudioStop(timestamp=timestamp + (samples * 1_000) // rate)


# -----------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--channels", type=int)
    parser.add_argument("--samples-per-chunk", type=int, default=1024)
    args = parser.parse_args()

    converter = AudioChunkConverter(
        rate=args.rate, width=args.width, channels=args.channels
    )

    with (
        io.BytesIO(sys.stdin.buffer.read()) as input_wav_io,
        io.BytesIO() as output_wav_io,
    ):
        input_wav_file: wave.Wave_read = wave.open(input_wav_io, "rb")
        output_wav_file: wave.Wave_write = wave.open(output_wav_io, "wb")
        with input_wav_file, output_wav_file:
            # Input
            rate = input_wav_file.getframerate()
            width = input_wav_file.getsampwidth()
            channels = input_wav_file.getnchannels()

            # Output
            output_wav_file.setframerate(args.rate if args.rate is not None else rate)
            output_wav_file.setsampwidth(
                args.width if args.width is not None else width
            )
            output_wav_file.setnchannels(
                args.channels if args.channels is not None else channels
            )

            audio_bytes = input_wav_file.readframes(args.samples_per_chunk)
            while audio_bytes:
                chunk = converter.convert(
                    AudioChunk(rate, width, channels, audio_bytes)
                )
                output_wav_file.writeframes(chunk.audio)
                audio_bytes = input_wav_file.readframes(args.samples_per_chunk)

        sys.stdout.buffer.write(output_wav_io.getvalue())


if __name__ == "__main__":
    main()
