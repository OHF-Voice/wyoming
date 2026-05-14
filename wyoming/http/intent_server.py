"""HTTP server for intent recognition/handling."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from flask import request

from wyoming.asr import Transcript
from wyoming.client import AsyncClient
from wyoming.error import Error
from wyoming.handle import Handled, NotHandled
from wyoming.intent import Intent, IntentsStart, IntentsStop, NotRecognized

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
    async def api_recognize_intent() -> Union[Dict[str, Any], List[Dict[str, Any]]]:
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

            type_name = "unknown"
            results: List[Dict[str, Any]] = []
            is_intent_list = False

            while True:
                event = await client.read_event()
                if event is None:
                    raise RuntimeError("Client disconnected")

                if IntentsStart.is_type(event.type):
                    is_intent_list = True
                    continue

                if Intent.is_type(event.type):
                    type_name = "intent"
                    intent = Intent.from_event(event)
                    results.append(intent.to_dict())
                    if not is_intent_list:
                        break

                if IntentsStop.is_type(event.type):
                    break

                if Handled.is_type(event.type):
                    type_name = "handled"
                    handled = Handled.from_event(event)
                    results.append(handled.to_dict())
                    break

                if NotRecognized.is_type(event.type):
                    type_name = "not-recognized"
                    not_recognized = NotRecognized.from_event(event)
                    results.append(not_recognized.to_dict())
                    break

                if NotHandled.is_type(event.type):
                    type_name = "not-handled"
                    not_handled = NotHandled.from_event(event)
                    results.append(not_handled.to_dict())
                    break

                if Error.is_type(event.type):
                    error = Error.from_event(event)
                    raise RuntimeError(
                        f"Unexpected error from client: code={error.code}, text={error.text}"
                    )

            if len(results) == 0:
                return {"success": False, "type": "unknown", "result": {}}

            if len(results) == 1:
                return {"success": True, "type": type_name, "result": results[0]}

            return {"success": True, "type": type_name, "result": results}

    app.run(args.host, args.port)


if __name__ == "__main__":
    main()
