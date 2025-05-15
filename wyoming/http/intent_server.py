"""HTTP server for intent recognition/handling."""

import logging
from pathlib import Path
from typing import Any, Dict

from flask import request

from wyoming.asr import Transcript
from wyoming.client import AsyncClient
from wyoming.error import Error
from wyoming.handle import Handled, NotHandled
from wyoming.intent import Intent, NotRecognized

from .shared import get_app, get_argument_parser

_DIR = Path(__file__).parent
CONF_PATH = _DIR / "conf" / "intent.yaml"


def main():
    parser = get_argument_parser()
    parser.add_argument("--language", help="Language for text")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    app = get_app("intent", CONF_PATH, args)

    @app.route("/api/recognize-intent", methods=["POST", "GET"])
    async def api_stt() -> Dict[str, Any]:
        uri = request.args.get("uri", args.uri)
        if not uri:
            raise ValueError("URI is required")

        if request.method == "POST":
            text = request.data.decode()
        else:
            text = request.args.get("text", "")

        if not text:
            raise ValueError("Text is required")

        language = request.args.get("language", args.language)

        async with AsyncClient.from_uri(uri) as client:
            await client.write_event(Transcript(text=text, language=language).event())

            while True:
                event = await client.read_event()
                if event is None:
                    raise RuntimeError("Client disconnected")

                success = False
                type_name = "unknown"
                result: Dict[str, Any] = {}

                if Intent.is_type(event.type):
                    success = True
                    type_name = "intent"
                    intent = Intent.from_event(event)
                    result = intent.to_dict()
                elif Handled.is_type(event.type):
                    success = True
                    type_name = "handled"
                    handled = Handled.from_event(event)
                    result = handled.to_dict()
                elif NotRecognized.is_type(event.type):
                    success = False
                    type_name = "not-recognized"
                    not_recognized = NotRecognized.from_event(event)
                    result = not_recognized.to_dict()
                elif NotHandled.is_type(event.type):
                    success = False
                    type_name = "not-handled"
                    not_handled = NotHandled.from_event(event)
                    result = not_handled.to_dict()
                elif Error.is_type(event.type):
                    error = Error.from_event(event)
                    raise RuntimeError(
                        f"Unexpected error from client: code={error.code}, text={error.text}"
                    )

                return {"success": success, "type": type_name, "result": result}

    app.run(args.host, args.port)


if __name__ == "__main__":
    main()
