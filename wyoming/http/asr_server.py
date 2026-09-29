"""HTTP server for automated speech recognition (ASR)."""

import io
import logging
import wave
from pathlib import Path
from typing import List, Optional

from flask import Response, jsonify, request

from wyoming.asr import (
    Transcribe,
    Transcript,
    TranscriptChunk,
    TranscriptStart,
    TranscriptStop,
)
from wyoming.audio import wav_to_chunks
from wyoming.error import Error

from .shared import check_args, get_app, get_argument_parser, get_client

_DIR = Path(__file__).parent
CONF_PATH = _DIR / "conf" / "asr.yaml"


def main():
    parser = get_argument_parser()
    parser.add_argument("--model", help="Default model name for transcription")
    parser.add_argument("--language", help="Default language for transcription")
    parser.add_argument("--samples-per-chunk", type=int, default=1024)
    args = parser.parse_args()
    check_args(parser, args)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    app = get_app("asr", CONF_PATH, args)

    @app.route("/api/speech-to-text", methods=["POST"])
    async def api_stt() -> Response:
        model_name = request.args.get("model", args.model)
        language = request.args.get("language", args.language)

        transcript_names: Optional[List[str]] = None
        transcript_names_str = request.args.get("transcript_names")
        if transcript_names_str:
            transcript_names = [
                name.strip() for name in transcript_names_str.split(",") if name.strip()
            ]

        transcript_terms: Optional[List[str]] = None
        transcript_terms_str = request.args.get("transcript_terms")
        if transcript_terms_str:
            transcript_terms = [
                term.strip() for term in transcript_terms_str.split(",") if term.strip()
            ]

        async with get_client(args) as client:
            await client.write_event(
                Transcribe(
                    name=model_name,
                    language=language,
                    transcript_names=transcript_names,
                    transcript_terms=transcript_terms,
                ).event()
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

            transcript: Optional[Transcript] = None
            transcript_chunks: List[str] = []
            is_streaming = False

            while True:
                event = await client.read_event()
                if event is None:
                    raise RuntimeError("Client disconnected")

                if Transcript.is_type(event.type):
                    transcript = Transcript.from_event(event)
                    if not is_streaming:
                        # Chunks are not coming
                        break
                elif TranscriptStart.is_type(event.type):
                    # Chunks will follow, so wait for the end of the stream
                    # instead of returning at the transcript.
                    is_streaming = True
                elif TranscriptChunk.is_type(event.type):
                    transcript_chunks.append(TranscriptChunk.from_event(event).text)
                elif TranscriptStop.is_type(event.type):
                    break
                elif Error.is_type(event.type):
                    error = Error.from_event(event)
                    raise RuntimeError(
                        f"Unexpected error from client: code={error.code}, text={error.text}"
                    )

            if transcript is None:
                # transcript is required, but fall back to the chunks so a
                # streaming service that omits it still gets a response. Each
                # chunk is the transcript so far, so the last one is the whole
                # transcript.
                if not is_streaming or not transcript_chunks:
                    raise RuntimeError("No transcript from service")

                transcript = Transcript(text=transcript_chunks[-1])

            result = transcript.to_dict()
            if is_streaming:
                result["chunks"] = transcript_chunks

            return jsonify(result)

    app.run(args.host, args.port)


if __name__ == "__main__":
    main()
