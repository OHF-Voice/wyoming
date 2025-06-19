"""Shared code for HTTP servers."""

import argparse
from pathlib import Path
from typing import Union

from flask import Flask, jsonify, redirect, request
from swagger_ui import flask_api_doc  # pylint: disable=no-name-in-module

from wyoming.client import AsyncClient
from wyoming.info import Describe, Info


def get_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser with shared arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--uri", help="URI of Wyoming service")
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG logs to console"
    )
    return parser


def get_app(
    name: str, openapi_config_path: Union[str, Path], args: argparse.Namespace
) -> Flask:
    """Create Flask app with default endpoints."""

    app = Flask(name)

    @app.route("/")
    def redirect_to_api():
        return redirect("/api")

    @app.route("/api/info", methods=["GET"])
    async def api_info():
        uri = request.args.get("uri", args.uri)
        if not uri:
            raise ValueError("URI is required")

        async with AsyncClient.from_uri(uri) as client:
            await client.write_event(Describe().event())

            while True:
                event = await client.read_event()
                if event is None:
                    raise RuntimeError("Client disconnected")

                if Info.is_type(event.type):
                    info = Info.from_event(event)
                    return jsonify(info.to_dict())

    @app.errorhandler(Exception)
    async def handle_error(err):
        """Return error as text."""
        return (f"{err.__class__.__name__}: {err}", 500)

    flask_api_doc(
        app, config_path=str(openapi_config_path), url_prefix="/api", title="API doc"
    )

    return app
