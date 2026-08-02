from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aviary.ledger import SQLiteLedger, canonical_json, utcnow
from aviary.simulation.contracts import ReplayResult, SimulationSnapshot


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class StoredSimulation:
    run_id: int
    result: ReplayResult
    receipt_valid: bool
    snapshot_integrity: tuple[bool, ...]

    @property
    def valid(self) -> bool:
        return self.receipt_valid and all(self.snapshot_integrity)


class SimulationReceiptStore:
    """Persist and verify deterministic simulation results in the Aviary ledger."""

    def __init__(self, ledger: SQLiteLedger):
        self.ledger = ledger

    def record(self, result: ReplayResult) -> int:
        existing = self.ledger.connection.execute(
            "SELECT id FROM simulation_runs WHERE receipt_sha256=?",
            (result.receipt_hash,),
        ).fetchone()
        if existing is not None:
            stored = self.load(int(existing[0]))
            if not stored.valid:
                raise ValueError(
                    f"simulation run {stored.run_id} failed integrity verification"
                )
            return stored.run_id

        final_state_json = canonical_json(_plain_json(result.final_state))
        now = utcnow()
        with self.ledger.connection:
            cur = self.ledger.connection.execute(
                "INSERT INTO simulation_runs(receipt_sha256,final_state_json,snapshot_count,created_at) VALUES(?,?,?,?)",
                (result.receipt_hash, final_state_json, len(result.snapshots), now),
            )
            run_id = int(cur.lastrowid)
            self.ledger.connection.executemany(
                "INSERT INTO simulation_snapshots(run_id,tick,state_json,state_sha256) VALUES(?,?,?,?)",
                [
                    (
                        run_id,
                        snapshot.tick,
                        canonical_json(_plain_json(snapshot.state)),
                        snapshot.state_hash,
                    )
                    for snapshot in result.snapshots
                ],
            )
            self.ledger.connection.execute(
                "INSERT INTO history(event_type,entity_id,payload_json,created_at) VALUES(?,?,?,?)",
                (
                    "simulation.recorded",
                    str(run_id),
                    canonical_json(
                        {
                            "receipt_sha256": result.receipt_hash,
                            "snapshot_count": len(result.snapshots),
                        }
                    ),
                    now,
                ),
            )
        return run_id

    def load(self, run_id: int) -> StoredSimulation:
        row = self.ledger.connection.execute(
            "SELECT id,receipt_sha256,final_state_json,snapshot_count FROM simulation_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise LookupError(f"simulation run {run_id} does not exist")

        snapshot_rows = self.ledger.connection.execute(
            "SELECT tick,state_json,state_sha256 FROM simulation_snapshots WHERE run_id=? ORDER BY tick",
            (run_id,),
        ).fetchall()
        if len(snapshot_rows) != int(row["snapshot_count"]):
            raise ValueError(
                f"simulation run {run_id} snapshot count does not match its receipt"
            )

        snapshots: list[SimulationSnapshot] = []
        snapshot_integrity: list[bool] = []
        for item in snapshot_rows:
            try:
                state = json.loads(item["state_json"])
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"simulation run {run_id} contains invalid snapshot JSON"
                ) from exc
            rebuilt = SimulationSnapshot.create(int(item["tick"]), state)
            snapshots.append(rebuilt)
            snapshot_integrity.append(rebuilt.state_hash == item["state_sha256"])

        try:
            final_state = json.loads(row["final_state_json"])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"simulation run {run_id} contains invalid final state JSON"
            ) from exc
        result = ReplayResult.create(tuple(snapshots), final_state)
        return StoredSimulation(
            run_id=run_id,
            result=result,
            receipt_valid=result.receipt_hash == row["receipt_sha256"],
            snapshot_integrity=tuple(snapshot_integrity),
        )
