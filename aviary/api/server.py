from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from aviary.ledger import SQLiteLedger
from aviary.registry import BirdRegistry
from aviary.simulation.persistence import SimulationReceiptStore


SQLITE_MAX_INTEGER = (1 << 63) - 1

CAPABILITIES = (
    {
        "method": "GET",
        "path": "/api/health",
        "purpose": "bridge readiness and discovered bird count",
    },
    {
        "method": "GET",
        "path": "/api/capabilities",
        "purpose": "machine-readable bridge feature discovery",
    },
    {
        "method": "GET",
        "path": "/api/birds",
        "purpose": "discovered bird contracts",
    },
    {
        "method": "GET",
        "path": "/api/simulations",
        "purpose": "paginated simulation receipt summaries",
    },
    {
        "method": "GET",
        "path": "/api/simulations/{run_id}",
        "purpose": "verified receipt detail with reconstructed state",
    },
    {
        "method": "GET",
        "path": "/api/simulations/{run_id}/verify",
        "purpose": "lightweight receipt integrity evidence",
    },
    {
        "method": "GET",
        "path": "/api/simulations/{run_id}/snapshots",
        "purpose": "paginated snapshot metadata with integrity evidence",
    },
    {
        "method": "GET",
        "path": "/api/simulations/{run_id}/snapshots/{tick}",
        "purpose": "one reconstructed snapshot with integrity evidence",
    },
)


class SnapshotNotFound(LookupError):
    """Raised when a run exists but does not contain the requested tick."""


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    return value


def _parse_run_id(raw_id: str) -> int:
    if not raw_id.isascii() or not raw_id.isdigit():
        raise ValueError("simulation run id must be a positive integer")
    run_id = int(raw_id)
    if not 1 <= run_id <= SQLITE_MAX_INTEGER:
        raise ValueError(
            f"simulation run id must be from 1 through {SQLITE_MAX_INTEGER}"
        )
    return run_id


def _parse_tick(raw_tick: str) -> int:
    if not raw_tick.isascii() or not raw_tick.isdigit():
        raise ValueError("simulation tick must be a non-negative integer")
    tick = int(raw_tick)
    if not 0 <= tick <= SQLITE_MAX_INTEGER:
        raise ValueError(f"simulation tick must be from 0 through {SQLITE_MAX_INTEGER}")
    return tick


class AviaryBridge:
    """Read-only application boundary for local Aviary clients."""

    def __init__(
        self,
        registry: BirdRegistry | None = None,
        ledger_path: str | Path = "ledger/aviary.db",
    ):
        self.registry = registry or BirdRegistry()
        if registry is None:
            self.registry.discover()
        self.ledger_path = Path(ledger_path)
        self._initialize_ledger()

    def _initialize_ledger(self) -> None:
        ledger = SQLiteLedger(self.ledger_path)
        try:
            SimulationReceiptStore(ledger)
        finally:
            ledger.close()

    def health(self) -> dict[str, Any]:
        return {
            "service": "the-aviary",
            "status": "ok",
            "api_version": "v1",
            "bird_count": len(self.registry.ids()),
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "service": "the-aviary",
            "api_version": "v1",
            "read_only": True,
            "capabilities": [dict(capability) for capability in CAPABILITIES],
            "count": len(CAPABILITIES),
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

    def simulations(self, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        ledger = SQLiteLedger(self.ledger_path)
        try:
            runs = SimulationReceiptStore(ledger).list_runs(limit=limit, offset=offset)
            return {
                "runs": [asdict(run) for run in runs],
                "count": len(runs),
                "limit": limit,
                "offset": offset,
            }
        finally:
            ledger.close()

    def simulation(self, run_id: int) -> dict[str, Any]:
        ledger = SQLiteLedger(self.ledger_path)
        try:
            stored = SimulationReceiptStore(ledger).load(run_id)
            return {
                "run_id": stored.run_id,
                "receipt_sha256": stored.result.receipt_hash,
                "receipt_valid": stored.receipt_valid,
                "snapshot_integrity": list(stored.snapshot_integrity),
                "valid": stored.valid,
                "final_state": _plain_json(stored.result.final_state),
                "snapshots": [
                    {
                        "tick": snapshot.tick,
                        "state": _plain_json(snapshot.state),
                        "state_sha256": snapshot.state_hash,
                        "valid": stored.snapshot_integrity[index],
                    }
                    for index, snapshot in enumerate(stored.result.snapshots)
                ],
            }
        finally:
            ledger.close()

    def simulation_verification(self, run_id: int) -> dict[str, Any]:
        ledger = SQLiteLedger(self.ledger_path)
        try:
            stored = SimulationReceiptStore(ledger).load(run_id)
            return {
                "run_id": stored.run_id,
                "receipt_sha256": stored.result.receipt_hash,
                "receipt_valid": stored.receipt_valid,
                "snapshot_count": len(stored.result.snapshots),
                "snapshot_integrity": list(stored.snapshot_integrity),
                "valid": stored.valid,
            }
        finally:
            ledger.close()

    def simulation_snapshots(
        self, run_id: int, *, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        ledger = SQLiteLedger(self.ledger_path)
        try:
            stored = SimulationReceiptStore(ledger).load(run_id)
            all_snapshots = [
                {
                    "tick": snapshot.tick,
                    "state_sha256": snapshot.state_hash,
                    "valid": stored.snapshot_integrity[index],
                }
                for index, snapshot in enumerate(stored.result.snapshots)
            ]
            snapshots = all_snapshots[offset : offset + limit]
            return {
                "run_id": stored.run_id,
                "receipt_sha256": stored.result.receipt_hash,
                "receipt_valid": stored.receipt_valid,
                "snapshots": snapshots,
                "count": len(snapshots),
                "total_count": len(all_snapshots),
                "limit": limit,
                "offset": offset,
            }
        finally:
            ledger.close()

    def simulation_snapshot(self, run_id: int, tick: int) -> dict[str, Any]:
        ledger = SQLiteLedger(self.ledger_path)
        try:
            stored = SimulationReceiptStore(ledger).load(run_id)
            for index, snapshot in enumerate(stored.result.snapshots):
                if snapshot.tick == tick:
                    return {
                        "run_id": stored.run_id,
                        "receipt_sha256": stored.result.receipt_hash,
                        "receipt_valid": stored.receipt_valid,
                        "tick": snapshot.tick,
                        "state": _plain_json(snapshot.state),
                        "state_sha256": snapshot.state_hash,
                        "valid": stored.snapshot_integrity[index],
                    }
            raise SnapshotNotFound(
                f"simulation snapshot not found: run_id={run_id} tick={tick}"
            )
        finally:
            ledger.close()


def _single_int_query(query: dict[str, list[str]], name: str, default: int) -> int:
    values = query.get(name)
    if values is None:
        return default
    if len(values) != 1:
        raise ValueError(f"{name} must be supplied once")
    try:
        value = int(values[0])
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    minimum = 1 if name == "limit" else 0
    if not minimum <= value <= SQLITE_MAX_INTEGER:
        raise ValueError(f"{name} must be from {minimum} through {SQLITE_MAX_INTEGER}")
    return value


def _handler_type(bridge: AviaryBridge) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "AviaryBridge/0.8"

        def do_GET(self) -> None:  # noqa: N802
            target = urlsplit(self.path)
            path = target.path
            if path == "/api/health":
                self._send_json(HTTPStatus.OK, bridge.health())
                return
            if path == "/api/capabilities":
                if target.query:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error": "invalid_request",
                            "detail": "capabilities does not accept query parameters",
                        },
                    )
                    return
                self._send_json(HTTPStatus.OK, bridge.capabilities())
                return
            if path == "/api/birds":
                self._send_json(HTTPStatus.OK, bridge.birds())
                return
            if path == "/api/simulations":
                self._handle_simulation_list(target.query)
                return
            if path.startswith("/api/simulations/"):
                self._handle_simulation_path(path, target.query)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": path})

        def _handle_simulation_list(self, raw_query: str) -> None:
            try:
                query = parse_qs(raw_query, keep_blank_values=True)
                limit = _single_int_query(query, "limit", 20)
                offset = _single_int_query(query, "offset", 0)
                if set(query) - {"limit", "offset"}:
                    raise ValueError("unsupported query parameter")
                payload = bridge.simulations(limit=limit, offset=offset)
            except ValueError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "invalid_request", "detail": str(exc)},
                )
                return
            except (OSError, RuntimeError, sqlite3.Error) as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "ledger_unavailable", "detail": str(exc)},
                )
                return
            self._send_json(HTTPStatus.OK, payload)

        def _handle_simulation_path(self, path: str, raw_query: str) -> None:
            suffix = path.removeprefix("/api/simulations/")
            segments = suffix.split("/")
            snapshot_list = len(segments) == 2 and segments[1] == "snapshots"
            if raw_query and not snapshot_list:
                self._send_invalid_simulation_path()
                return
            try:
                if len(segments) == 1:
                    run_id = _parse_run_id(segments[0])
                    payload = bridge.simulation(run_id)
                elif len(segments) == 2 and segments[1] == "verify":
                    run_id = _parse_run_id(segments[0])
                    payload = bridge.simulation_verification(run_id)
                elif snapshot_list:
                    run_id = _parse_run_id(segments[0])
                    query = parse_qs(raw_query, keep_blank_values=True)
                    limit = _single_int_query(query, "limit", 20)
                    offset = _single_int_query(query, "offset", 0)
                    if set(query) - {"limit", "offset"}:
                        raise ValueError("unsupported query parameter")
                    payload = bridge.simulation_snapshots(
                        run_id, limit=limit, offset=offset
                    )
                elif len(segments) == 3 and segments[1] == "snapshots":
                    run_id = _parse_run_id(segments[0])
                    tick = _parse_tick(segments[2])
                    payload = bridge.simulation_snapshot(run_id, tick)
                else:
                    self._send_invalid_simulation_path()
                    return
            except ValueError as exc:
                if str(exc).startswith((
                    "simulation run id",
                    "simulation tick",
                    "limit",
                    "offset",
                    "unsupported query parameter",
                )):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "invalid_request", "detail": str(exc)},
                    )
                else:
                    self._send_json(
                        HTTPStatus.CONFLICT,
                        {"error": "simulation_invalid", "detail": str(exc)},
                    )
                return
            except SnapshotNotFound as exc:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "snapshot_not_found", "detail": str(exc)},
                )
                return
            except LookupError as exc:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "simulation_not_found", "detail": str(exc)},
                )
                return
            except (OSError, RuntimeError, sqlite3.Error) as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "ledger_unavailable", "detail": str(exc)},
                )
                return
            self._send_json(HTTPStatus.OK, payload)

        def _send_invalid_simulation_path(self) -> None:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": "invalid_request",
                    "detail": "invalid simulation resource path",
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            self._send_json(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {"error": "method_not_allowed", "method": "POST"},
            )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
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
    ledger_path: str | Path = "ledger/aviary.db",
) -> ThreadingHTTPServer:
    if not isinstance(host, str) or not host.strip():
        raise ValueError("host cannot be empty")
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 through 65535")
    service = bridge or AviaryBridge(ledger_path=ledger_path)
    return ThreadingHTTPServer((host, port), _handler_type(service))
