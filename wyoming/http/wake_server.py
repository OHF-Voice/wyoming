"""HTTP server for wake word detection."""

import io
import logging
import wave
from pathlib import Path

from flask import Response, jsonify, request

from wyoming.audio import wav_to_chunks
from wyoming.client import AsyncClient
from wyoming.error import Error
from wyoming.wake import Detect, Detection, NotDetected

from .shared import get_app, get_argument_parser

_DIR = Path(__file__).parent
CONF_PATH = _DIR / "conf" / "wake.yaml"


def main():
    parser = get_argument_parser()
    parser.add_argument("--wake-word-name", action="append")
    parser.add_argument("--samples-per-chunk", type=int, default=1024)
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    app = get_app("wake", CONF_PATH, args)

    @app.route("/api/detect-wake-word", methods=["POST", "GET"])
    async def api_wake() -> Response:
        uri = request.args.get("uri", args.uri)
        if not uri:
            raise ValueError("URI is required")

        async with AsyncClient.from_uri(uri) as client:
            if args.wake_word_name:
                await client.write_event(Detect(args.wake_word_name).event())

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

                if Detection.is_type(event.type) or NotDetected.is_type(event.type):
                    return jsonify(event.to_dict())

                if Error.is_type(event.type):
                    error = Error.from_event(event)
                    raise RuntimeError(
                        f"Unexpected error from client: code={error.code}, text={error.text}"
                    )

    app.run(args.host, args.port)


if __name__ == "__main__":
    main()
