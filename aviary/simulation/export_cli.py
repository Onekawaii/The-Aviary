from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
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
        "snapshot_integrity": list(stored.snapshot_integrity),
        "snapshots": [
            {
                "tick": snapshot.tick,
                "state": _plain(snapshot.state),
                "state_sha256": snapshot.state_hash,
            }
            for snapshot in stored.result.snapshots
        ],
        "final_state": _plain(stored.result.final_state),
    }


def _write_atomic(path: Path, content: str) -> None:
    parent = path.parent
    descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation.export_cli",
        description="Export one persisted simulation receipt as canonical JSON.",
    )
    parser.add_argument("run_id", type=int)
    parser.add_argument("--db", type=Path, default=default_db_path())
    parser.add_argument(
        "--output",
        type=Path,
        help="Atomically replace this file with the exported JSON instead of writing to stdout.",
    )
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

    encoded = json.dumps(as_dict(stored), indent=2, sort_keys=True)
    try:
        if args.output is None:
            print(encoded)
        else:
            _write_atomic(args.output, encoded)
    except OSError as exc:
        print(f"ERROR: could not write export: {exc}", file=sys.stderr)
        return 2
    return 0 if stored.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
