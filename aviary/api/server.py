from __future__ import annotations

import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from aviary.registry import BirdRegistry


class AviaryBridge:
    """Read-only application boundary for local Aviary clients."""

    def __init__(self, registry: BirdRegistry | None = None):
        self.registry = registry or BirdRegistry()
        if registry is None:
            self.registry.discover()

    def health(self) -> dict[str, Any]:
        return {
            "service": "the-aviary",
            "status": "ok",
            "api_version": "v1",
            "bird_count": len(self.registry.ids()),
        }

    def birds(self) -> dict[str, Any]:
        birds = []
        for loaded in self.registry.all():
            metadata = loaded.instance.metadata()
            birds.append(
                {
                    "bird_id": loaded.bird_id,
                    "module": loaded.module,
                    "metadata": asdict(metadata),
                    "voice": loaded.instance.voice(),
                    "schema": loaded.instance.schema(),
                }
            )
        return {"birds": birds, "count": len(birds)}


def _handler_type(bridge: AviaryBridge) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "AviaryBridge/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            path = urlsplit(self.path).path
            if path == "/api/health":
                self._send_json(HTTPStatus.OK, bridge.health())
                return
            if path == "/api/birds":
                self._send_json(HTTPStatus.OK, bridge.birds())
                return
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error": "not_found", "path": path},
            )

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
            self._send_json(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {"error": "method_not_allowed", "method": "POST"},
            )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def create_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    bridge: AviaryBridge | None = None,
) -> ThreadingHTTPServer:
    if not isinstance(host, str) or not host.strip():
        raise ValueError("host cannot be empty")
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 through 65535")
    service = bridge or AviaryBridge()
    return ThreadingHTTPServer((host, port), _handler_type(service))
