from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aviary.simulation.contracts import (
    ReplayResult,
    SimulationSnapshot,
    SimulationValidationError,
)


@dataclass(frozen=True, slots=True)
class ExportVerification:
    run_id: int
    valid: bool
    receipt_valid: bool
    receipt_sha256: str
    snapshot_integrity: tuple[bool, ...]
    claims_match: bool


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _require_hash(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_name} must be a 64-character SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a 64-character SHA-256 hex digest") from exc
    return value.lower()


def verify_payload(payload: Any) -> ExportVerification:
    root = _require_mapping(payload, "export")

    run_id = root.get("run_id")
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id < 1:
        raise ValueError("run_id must be a positive integer")

    snapshots_value = root.get("snapshots")
    if not isinstance(snapshots_value, list):
        raise ValueError("snapshots must be a JSON array")

    snapshots: list[SimulationSnapshot] = []
    snapshot_integrity: list[bool] = []
    previous_tick = -1
    for index, raw_snapshot in enumerate(snapshots_value):
        item = _require_mapping(raw_snapshot, f"snapshots[{index}]")
        tick = item.get("tick")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError(f"snapshots[{index}].tick must be a non-negative integer")
        if tick <= previous_tick:
            raise ValueError("snapshot ticks must be strictly increasing")
        previous_tick = tick
        state = _require_mapping(item.get("state"), f"snapshots[{index}].state")
        declared_hash = _require_hash(
            item.get("state_sha256"), f"snapshots[{index}].state_sha256"
        )
        rebuilt = SimulationSnapshot.create(tick, state)
        snapshots.append(rebuilt)
        snapshot_integrity.append(rebuilt.state_hash == declared_hash)

    final_state = _require_mapping(root.get("final_state"), "final_state")
    rebuilt_result = ReplayResult.create(tuple(snapshots), final_state)
    declared_receipt = _require_hash(root.get("receipt_sha256"), "receipt_sha256")
    receipt_valid = rebuilt_result.receipt_hash == declared_receipt

    declared_snapshot_integrity = root.get("snapshot_integrity")
    if not isinstance(declared_snapshot_integrity, list) or any(
        not isinstance(item, bool) for item in declared_snapshot_integrity
    ):
        raise ValueError("snapshot_integrity must be a JSON array of booleans")
    if len(declared_snapshot_integrity) != len(snapshot_integrity):
        raise ValueError("snapshot_integrity length must match snapshots")

    declared_receipt_valid = _require_bool(root.get("receipt_valid"), "receipt_valid")
    declared_valid = _require_bool(root.get("valid"), "valid")
    computed_valid = receipt_valid and all(snapshot_integrity)
    claims_match = (
        declared_snapshot_integrity == snapshot_integrity
        and declared_receipt_valid == receipt_valid
        and declared_valid == computed_valid
    )

    return ExportVerification(
        run_id=run_id,
        valid=computed_valid and claims_match,
        receipt_valid=receipt_valid,
        receipt_sha256=rebuilt_result.receipt_hash,
        snapshot_integrity=tuple(snapshot_integrity),
        claims_match=claims_match,
    )


def as_dict(result: ExportVerification) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "valid": result.valid,
        "receipt_valid": result.receipt_valid,
        "receipt_sha256": result.receipt_sha256,
        "snapshot_integrity": list(result.snapshot_integrity),
        "claims_match": result.claims_match,
    }


def print_result(result: ExportVerification) -> None:
    print("THE AVIARY — EXPORTED SIMULATION RECEIPT")
    print(f"Run: {result.run_id}")
    print(f"Integrity: {'PASS' if result.valid else 'FAIL'}")
    print(f"Snapshots: {len(result.snapshot_integrity)}")
    print(f"Claims: {'MATCH' if result.claims_match else 'MISMATCH'}")
    print(f"Receipt: sha256:{result.receipt_sha256}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation.verify_export_cli",
        description="Independently verify an exported simulation receipt JSON file.",
    )
    parser.add_argument("export", type=Path, help="path to an exported receipt JSON file")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.export.read_text(encoding="utf-8"))
        result = verify_payload(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, SimulationValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(as_dict(result), indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print_result(result)
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
