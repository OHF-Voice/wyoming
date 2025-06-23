"""HTTP server for automated speech recognition (ASR)."""

import io
import logging
import wave
from pathlib import Path

from flask import Response, jsonify, request

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import wav_to_chunks
from wyoming.client import AsyncClient
from wyoming.error import Error

from .shared import get_app, get_argument_parser

_DIR = Path(__file__).parent
CONF_PATH = _DIR / "conf" / "asr.yaml"


def main():
    parser = get_argument_parser()
    parser.add_argument("--model", help="Default model name for transcription")
    parser.add_argument("--language", help="Default language for transcription")
    parser.add_argument("--samples-per-chunk", type=int, default=1024)
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    app = get_app("asr", CONF_PATH, args)

    @app.route("/api/speech-to-text", methods=["POST"])
    async def api_stt() -> Response:
        uri = request.args.get("uri", args.uri)
        if not uri:
            raise ValueError("URI is required")

        model_name = request.args.get("model", args.model)
        language = request.args.get("language", args.model)

        async with AsyncClient.from_uri(uri) as client:
            await client.write_event(
                Transcribe(name=model_name, language=language).event()
            )

            with io.BytesIO(request.data) as wav_io:
                with wave.open(wav_io, "rb") as wav_file:
                    chunks = wav_to_chunks(
                        wav_file,
                        samples_per_chunk=args.samples_per_chunk,
                        start_event=True,
                        stop_event=True,
                    )
                    for chunk in chunks:
                        await client.write_event(chunk.event())

            while True:
                event = await client.read_event()
                if event is None:
                    raise RuntimeError("Client disconnected")

                if Transcript.is_type(event.type):
                    transcript = Transcript.from_event(event)
                    return jsonify(transcript.to_dict())

                if Error.is_type(event.type):
                    error = Error.from_event(event)
                    raise RuntimeError(
                        f"Unexpected error from client: code={error.code}, text={error.text}"
                    )

    app.run(args.host, args.port)


if __name__ == "__main__":
    main()
