from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from aviary.cli import default_db_path
from aviary.ledger import SQLiteLedger
from aviary.simulation.persistence import SimulationReceiptStore, StoredSimulation


def as_dict(stored: StoredSimulation) -> dict[str, Any]:
    return {
        "run_id": stored.run_id,
        "valid": stored.valid,
        "receipt_valid": stored.receipt_valid,
        "receipt_sha256": stored.result.receipt_hash,
        "snapshot_integrity": list(stored.snapshot_integrity),
        "snapshots": [
            {
                "tick": snapshot.tick,
                "state": snapshot.state,
                "state_sha256": snapshot.state_hash,
            }
            for snapshot in stored.result.snapshots
        ],
        "final_state": stored.result.final_state,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation.export_cli",
        description="Export one persisted simulation receipt as canonical JSON.",
    )
    parser.add_argument("run_id", type=int)
    parser.add_argument("--db", type=Path, default=default_db_path())
    args = parser.parse_args(argv)

    ledger: SQLiteLedger | None = None
    try:
        ledger = SQLiteLedger(args.db)
        stored = SimulationReceiptStore(ledger).load(args.run_id)
    except (OSError, sqlite3.Error, RuntimeError, LookupError, ValueError, OverflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if ledger is not None:
            ledger.close()

    print(json.dumps(as_dict(stored), indent=2, sort_keys=True))
    return 0 if stored.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
