from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aviary.cli import default_db_path
from aviary.ledger import SQLiteLedger
from aviary.simulation.contracts import (
    EntityBlueprint,
    SimulationEvent,
    SimulationValidationError,
)
from aviary.simulation.kernel import DeterministicSimulation
from aviary.simulation.persistence import SimulationReceiptStore


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SimulationValidationError(f"{name} must be a JSON object")
    return value


def _array(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise SimulationValidationError(f"{name} must be a JSON array")
    return value


def _load_spec(path: Path) -> tuple[tuple[EntityBlueprint, ...], tuple[SimulationEvent, ...], int | None]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SimulationValidationError(f"cannot read simulation spec: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SimulationValidationError(
            f"simulation spec is invalid JSON at line {exc.lineno} column {exc.colno}"
        ) from exc

    document = _object(raw, "simulation spec")
    blueprints_raw = _array(document.get("blueprints"), "blueprints")
    events_raw = _array(document.get("events"), "events")

    blueprints: list[EntityBlueprint] = []
    for index, value in enumerate(blueprints_raw):
        item = _object(value, f"blueprints[{index}]")
        try:
            blueprints.append(
                EntityBlueprint(
                    entity_id=item["entity_id"],
                    kind=item["kind"],
                    state=item.get("state", {}),
                )
            )
        except KeyError as exc:
            raise SimulationValidationError(
                f"blueprints[{index}] is missing {exc.args[0]!r}"
            ) from exc

    events: list[SimulationEvent] = []
    for index, value in enumerate(events_raw):
        item = _object(value, f"events[{index}]")
        try:
            events.append(
                SimulationEvent(
                    event_id=item["event_id"],
                    tick=item["tick"],
                    kind=item["kind"],
                    target_id=item["target_id"],
                    payload=item.get("payload", {}),
                )
            )
        except KeyError as exc:
            raise SimulationValidationError(
                f"events[{index}] is missing {exc.args[0]!r}"
            ) from exc

    until_tick = document.get("until_tick")
    return tuple(blueprints), tuple(events), until_tick


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation.run_cli",
        description="Run a deterministic simulation JSON spec and persist its receipt.",
    )
    parser.add_argument("spec", type=Path, help="path to the simulation JSON spec")
    parser.add_argument("--db", type=Path, default=default_db_path())
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        blueprints, events, until_tick = _load_spec(args.spec)
        result = DeterministicSimulation().replay(
            blueprints,
            events,
            until_tick=until_tick,
        )
    except (SimulationValidationError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    ledger = SQLiteLedger(args.db)
    try:
        store = SimulationReceiptStore(ledger)
        run_id = store.record(result)
        stored = store.load(run_id)
    except (LookupError, ValueError, OverflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        ledger.close()

    payload = {
        "run_id": run_id,
        "valid": stored.valid,
        "receipt_sha256": stored.result.receipt_hash,
        "snapshot_count": len(stored.result.snapshots),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("THE AVIARY — SIMULATION RECORDED")
        print(f"Run: {run_id}")
        print(f"Integrity: {'PASS' if stored.valid else 'FAIL'}")
        print(f"Snapshots: {payload['snapshot_count']}")
        print(f"Receipt: sha256:{payload['receipt_sha256']}")
    return 0 if stored.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
