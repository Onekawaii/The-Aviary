from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aviary.cli import default_db_path
from aviary.ledger import SQLiteLedger
from aviary.simulation.persistence import SimulationReceiptStore, StoredSimulation


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def as_dict(stored: StoredSimulation) -> dict[str, Any]:
    return {
        "run_id": stored.run_id,
        "valid": stored.valid,
        "receipt_valid": stored.receipt_valid,
        "receipt_sha256": stored.result.receipt_hash,
        "snapshot_count": len(stored.result.snapshots),
        "snapshot_integrity": list(stored.snapshot_integrity),
        "final_state": _plain(stored.result.final_state),
    }


def print_stored(stored: StoredSimulation) -> None:
    status = "PASS" if stored.valid else "FAIL"
    print("THE AVIARY — SIMULATION RECEIPT")
    print(f"Run: {stored.run_id}")
    print(f"Integrity: {status}")
    print(f"Snapshots: {len(stored.result.snapshots)}")
    print(f"Receipt: sha256:{stored.result.receipt_hash}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation.cli",
        description="Load and verify a persisted deterministic simulation receipt.",
    )
    parser.add_argument("run_id", type=int, help="numeric simulation run ID")
    parser.add_argument("--db", type=Path, default=default_db_path())
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    ledger = SQLiteLedger(args.db)
    try:
        try:
            stored = SimulationReceiptStore(ledger).load(args.run_id)
        except (LookupError, ValueError, OverflowError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(as_dict(stored), indent=2, sort_keys=True, ensure_ascii=True))
        else:
            print_stored(stored)
        return 0 if stored.valid else 1
    finally:
        ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
