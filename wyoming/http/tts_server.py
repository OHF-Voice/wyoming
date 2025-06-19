"""HTTP server for text to speech (TTS)."""

import io
import logging
import wave
from pathlib import Path
from typing import Optional

from flask import Response, request

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncClient
from wyoming.error import Error
from wyoming.tts import Synthesize, SynthesizeVoice

from .shared import get_app, get_argument_parser

_DIR = Path(__file__).parent
CONF_PATH = _DIR / "conf" / "tts.yaml"


def main():
    parser = get_argument_parser()
    parser.add_argument("--voice", help="Default voice for synthesis")
    parser.add_argument("--speaker", help="Default voice speaker for synthesis")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    app = get_app("tts", CONF_PATH, args)

    @app.route("/api/text-to-speech", methods=["POST", "GET"])
    async def api_stt() -> Response:
        uri = request.args.get("uri", args.uri)
        if not uri:
            raise ValueError("URI is required")

        if request.method == "POST":
            text = request.data.decode()
        else:
            text = request.args.get("text", "")

        if not text:
            raise ValueError("Text is required")

        voice: Optional[SynthesizeVoice] = None
        voice_name = request.args.get("voice", args.voice)
        if voice_name:
            voice = SynthesizeVoice(
                name=voice_name, speaker=request.args.get("speaker", args.speaker)
            )

        async with AsyncClient.from_uri(uri) as client:
            wav_io = io.BytesIO()
            wav_file = wave.open(wav_io, "wb")
            await client.write_event(Synthesize(text=text, voice=voice).event())

            while True:
                event = await client.read_event()
                if event is None:
                    raise RuntimeError("Client disconnected")

                if AudioStart.is_type(event.type):
                    audio_start = AudioStart.from_event(event)
                    wav_file.setframerate(audio_start.rate)
                    wav_file.setsampwidth(audio_start.width)
                    wav_file.setnchannels(audio_start.channels)
                elif AudioChunk.is_type(event.type):
                    audio_chunk = AudioChunk.from_event(event)
                    wav_file.writeframes(audio_chunk.audio)
                elif AudioStop.is_type(event.type):
                    wav_file.close()
                    wav_io.seek(0)
                    return Response(
                        wav_io.getvalue(), headers={"Content-Type": "audio/wav"}
                    )
                elif Error.is_type(event.type):
                    error = Error.from_event(event)
                    raise RuntimeError(
                        f"Unexpected error from client: code={error.code}, text={error.text}"
                    )

    app.run(args.host, args.port)


if __name__ == "__main__":
    main()
