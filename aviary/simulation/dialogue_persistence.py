from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aviary.ledger import SQLiteLedger, canonical_json, utcnow
from aviary.simulation.contracts import SimulationEvent
from aviary.simulation.dialogue import DialogueRecord, DialogueResult


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    return value


def _document_json(result: DialogueResult) -> str:
    document = {
        "records": [
            {
                "event_id": record.event_id,
                "tick": record.tick,
                "kind": record.kind,
                "target_id": record.target_id,
                "payload": _plain_json(record.payload),
                "decision": record.decision,
                "reason": record.reason,
            }
            for record in result.records
        ],
        "accepted_events": [
            {
                "event_id": event.event_id,
                "tick": event.tick,
                "kind": event.kind,
                "target_id": event.target_id,
                "payload": _plain_json(event.payload),
            }
            for event in result.accepted_events
        ],
    }
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


@dataclass(frozen=True, slots=True)
class StoredDialogue:
    dialogue_id: int
    result: DialogueResult
    receipt_valid: bool

    @property
    def valid(self) -> bool:
        return self.receipt_valid


class DialogueReceiptStore:
    """Persist and independently verify deterministic dialogue receipts."""

    def __init__(self, ledger: SQLiteLedger):
        self.ledger = ledger

    def record(self, result: DialogueResult) -> int:
        if not isinstance(result, DialogueResult):
            raise TypeError("result must be a DialogueResult")

        existing = self.ledger.connection.execute(
            "SELECT id FROM dialogue_runs WHERE receipt_sha256=?",
            (result.receipt_hash,),
        ).fetchone()
        if existing is not None:
            stored = self.load(int(existing[0]))
            if not stored.valid:
                raise ValueError(
                    f"dialogue run {stored.dialogue_id} failed integrity verification"
                )
            return stored.dialogue_id

        now = utcnow()
        document_json = _document_json(result)
        with self.ledger.connection:
            cur = self.ledger.connection.execute(
                "INSERT INTO dialogue_runs(receipt_sha256,document_json,record_count,accepted_count,created_at) VALUES(?,?,?,?,?)",
                (
                    result.receipt_hash,
                    document_json,
                    len(result.records),
                    len(result.accepted_events),
                    now,
                ),
            )
            dialogue_id = int(cur.lastrowid)
            self.ledger.connection.execute(
                "INSERT INTO history(event_type,entity_id,payload_json,created_at) VALUES(?,?,?,?)",
                (
                    "dialogue.recorded",
                    str(dialogue_id),
                    canonical_json(
                        {
                            "receipt_sha256": result.receipt_hash,
                            "record_count": len(result.records),
                            "accepted_count": len(result.accepted_events),
                        }
                    ),
                    now,
                ),
            )
        return dialogue_id

    def load(self, dialogue_id: int) -> StoredDialogue:
        row = self.ledger.connection.execute(
            "SELECT id,receipt_sha256,document_json,record_count,accepted_count FROM dialogue_runs WHERE id=?",
            (dialogue_id,),
        ).fetchone()
        if row is None:
            raise LookupError(f"dialogue run {dialogue_id} does not exist")

        try:
            document = json.loads(row["document_json"])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"dialogue run {dialogue_id} contains invalid document JSON"
            ) from exc
        if not isinstance(document, dict):
            raise ValueError(f"dialogue run {dialogue_id} document must be an object")

        record_items = document.get("records")
        accepted_items = document.get("accepted_events")
        if not isinstance(record_items, list) or not isinstance(accepted_items, list):
            raise ValueError(
                f"dialogue run {dialogue_id} document has invalid collections"
            )
        if len(record_items) != int(row["record_count"]):
            raise ValueError(
                f"dialogue run {dialogue_id} record count does not match its receipt"
            )
        if len(accepted_items) != int(row["accepted_count"]):
            raise ValueError(
                f"dialogue run {dialogue_id} accepted count does not match its receipt"
            )

        try:
            records = tuple(
                DialogueRecord(
                    event_id=item["event_id"],
                    tick=item["tick"],
                    kind=item["kind"],
                    target_id=item["target_id"],
                    payload=item["payload"],
                    decision=item["decision"],
                    reason=item["reason"],
                )
                for item in record_items
            )
            accepted_events = tuple(
                SimulationEvent(
                    event_id=item["event_id"],
                    tick=item["tick"],
                    kind=item["kind"],
                    target_id=item["target_id"],
                    payload=item["payload"],
                )
                for item in accepted_items
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"dialogue run {dialogue_id} document is structurally invalid"
            ) from exc

        result = DialogueResult.create(records, accepted_events)
        return StoredDialogue(
            dialogue_id=dialogue_id,
            result=result,
            receipt_valid=result.receipt_hash == row["receipt_sha256"],
        )
