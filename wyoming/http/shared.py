"""Shared code for HTTP servers.

These servers are unauthenticated by design and are intended to run on a
trusted network only. See SECURITY.md.
"""

import argparse
import logging
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, request
from swagger_ui import flask_api_doc  # pylint: disable=no-name-in-module
from werkzeug.exceptions import BadRequest, HTTPException

from wyoming.client import AsyncClient
from wyoming.info import Describe, Info

_LOGGER = logging.getLogger(__name__)

# Schemes a request is allowed to ask for. 'stdio://' is excluded because it is
# meaningless for an HTTP server and would consume the server's own stdin.
_REQUEST_URI_SCHEMES = ("tcp", "unix")


def get_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser with shared arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--uri", help="URI of Wyoming service (required without --allow-uri-override)"
    )
    parser.add_argument(
        "--allow-uri-override",
        action="store_true",
        help="Allow each request to select the Wyoming service with the 'uri' "
        "query parameter. Any client can then make this server connect to any "
        "address it can reach, so only use this on a trusted network.",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait when connecting to a Wyoming service (default: 10)",
    )
    parser.add_argument(
        "--read-timeout",
        type=float,
        default=300.0,
        help="Seconds to wait for each event from a Wyoming service. "
        "Applies per event, not to the request as a whole. "
        "Use 0 to wait indefinitely (default: 300)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG logs to console"
    )
    return parser


def check_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Verify that a Wyoming service can be determined for incoming requests."""
    if not (args.uri or args.allow_uri_override):
        parser.error(
            "--uri is required, or use --allow-uri-override to let each request "
            "select the Wyoming service (only do this on a trusted network)"
        )


def get_uri(args: argparse.Namespace) -> str:
    """Determine which Wyoming service the current request should use.

    A request may only choose the service if the operator opted in with
    --allow-uri-override. Otherwise the configured --uri is always used.
    """
    request_uri = request.args.get("uri")
    if request_uri:
        if not args.allow_uri_override:
            raise BadRequest(
                "This server does not allow requests to select the Wyoming "
                "service. It must be started with --allow-uri-override."
            )

        if urlparse(request_uri).scheme not in _REQUEST_URI_SCHEMES:
            raise BadRequest(
                "uri must be one of: "
                + ", ".join(f"{scheme}://" for scheme in _REQUEST_URI_SCHEMES)
            )

        return request_uri

    if not args.uri:
        raise BadRequest("uri is required")

    return args.uri


def get_client(args: argparse.Namespace) -> AsyncClient:
    """Create a Wyoming client for the current request."""
    return AsyncClient.from_uri(
        get_uri(args),
        # 0 disables the timeout. Without one, a service that accepts the
        # connection but never responds occupies the worker indefinitely.
        connect_timeout=args.connect_timeout or None,
        read_timeout=args.read_timeout or None,
    )


def get_app(
    name: str, openapi_config_path: Union[str, Path], args: argparse.Namespace
) -> Flask:
    """Create Flask app with default endpoints."""
    if not (args.uri or args.allow_uri_override):
        raise ValueError(
            "Either 'uri' must be set, or 'allow_uri_override' must be enabled"
        )

    app = Flask(name)

    @app.route("/")
    def redirect_to_api():
        return redirect("/api")

    @app.route("/api/info", methods=["GET"])
    async def api_info():
        async with get_client(args) as client:
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
        if isinstance(err, HTTPException):
            # Raised deliberately, so the description is safe to return
            return (f"{err.name}: {err.description}", err.code)

        # Log server-side only: the message may describe hosts and services that
        # the client should not learn about.
        _LOGGER.exception("Unexpected error while handling request")
        return ("Internal Server Error", 500)

    flask_api_doc(
        app, config_path=str(openapi_config_path), url_prefix="/api", title="API doc"
    )

    return app
