from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from aviary.cli import default_db_path
from aviary.ledger import SQLiteLedger
from aviary.simulation.persistence import SimulationReceiptStore, SimulationRunSummary


def as_dict(summary: SimulationRunSummary) -> dict[str, object]:
    return {
        "run_id": summary.run_id,
        "receipt_sha256": summary.receipt_sha256,
        "snapshot_count": summary.snapshot_count,
        "created_at": summary.created_at,
    }


def print_runs(runs: tuple[SimulationRunSummary, ...]) -> None:
    print("THE AVIARY — SIMULATION RUNS")
    if not runs:
        print("No persisted simulation runs.")
        return
    for run in runs:
        print(
            f"Run {run.run_id} | snapshots={run.snapshot_count} | "
            f"created={run.created_at} | sha256:{run.receipt_sha256}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation.list_cli",
        description="List persisted deterministic simulation receipts.",
    )
    parser.add_argument("--db", type=Path, default=default_db_path())
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    ledger: SQLiteLedger | None = None
    try:
        ledger = SQLiteLedger(args.db)
        runs = SimulationReceiptStore(ledger).list_runs(
            limit=args.limit,
            offset=args.offset,
        )
    except (OSError, sqlite3.Error, ValueError, OverflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if ledger is not None:
            ledger.close()

    if args.json:
        print(json.dumps([as_dict(run) for run in runs], indent=2, sort_keys=True))
    else:
        print_runs(runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
