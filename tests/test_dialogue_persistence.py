from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aviary.ledger import SQLiteLedger
from aviary.simulation import (
    DeterministicDialogue,
    DialogueReceiptStore,
    GovernorVerdict,
    SimulationEvent,
)


class DialoguePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.ledger = SQLiteLedger(Path(self.tempdir.name) / "aviary.db")
        self.store = DialogueReceiptStore(self.ledger)
        self.result = DeterministicDialogue().deliberate(
            (
                SimulationEvent("move", 1, "set_property", "ape-1", {"key": "x", "value": 2}),
                SimulationEvent("sleep", 2, "set_property", "ape-1", {"key": "awake", "value": False}),
            ),
            lambda event: GovernorVerdict(
                event.event_id == "move",
                "allowed" if event.event_id == "move" else "blocked",
            ),
        )

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def test_schema_migrates_to_dialogue_receipts(self):
        self.assertEqual(self.ledger.get_schema_version(), 4)

    def test_record_and_load_preserve_verified_dialogue(self):
        dialogue_id = self.store.record(self.result)
        stored = self.store.load(dialogue_id)
        self.assertTrue(stored.valid)
        self.assertEqual(stored.result, self.result)
        self.assertEqual(stored.result.receipt_hash, self.result.receipt_hash)

    def test_record_is_idempotent_for_same_receipt(self):
        first = self.store.record(self.result)
        second = self.store.record(self.result)
        self.assertEqual(first, second)
        row = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM dialogue_runs"
        ).fetchone()
        self.assertEqual(int(row[0]), 1)

    def test_history_receipt_is_recorded(self):
        dialogue_id = self.store.record(self.result)
        row = self.ledger.connection.execute(
            "SELECT event_type,entity_id,payload_json FROM history WHERE event_type='dialogue.recorded'"
        ).fetchone()
        self.assertEqual(row["entity_id"], str(dialogue_id))
        payload = json.loads(row["payload_json"])
        self.assertEqual(payload["receipt_sha256"], self.result.receipt_hash)
        self.assertEqual(payload["record_count"], 2)
        self.assertEqual(payload["accepted_count"], 1)

    def test_tampered_document_is_reported_invalid(self):
        dialogue_id = self.store.record(self.result)
        row = self.ledger.connection.execute(
            "SELECT document_json FROM dialogue_runs WHERE id=?",
            (dialogue_id,),
        ).fetchone()
        document = json.loads(row["document_json"])
        document["records"][1]["reason"] = "secretly allowed"
        with self.ledger.connection:
            self.ledger.connection.execute(
                "UPDATE dialogue_runs SET document_json=? WHERE id=?",
                (json.dumps(document, sort_keys=True, separators=(",", ":")), dialogue_id),
            )
        stored = self.store.load(dialogue_id)
        self.assertFalse(stored.valid)
        self.assertNotEqual(stored.result.receipt_hash, self.result.receipt_hash)

    def test_tampered_count_fails_cleanly(self):
        dialogue_id = self.store.record(self.result)
        with self.ledger.connection:
            self.ledger.connection.execute(
                "UPDATE dialogue_runs SET record_count=99 WHERE id=?",
                (dialogue_id,),
            )
        with self.assertRaisesRegex(ValueError, "record count"):
            self.store.load(dialogue_id)

    def test_invalid_json_fails_cleanly(self):
        dialogue_id = self.store.record(self.result)
        with self.ledger.connection:
            self.ledger.connection.execute(
                "UPDATE dialogue_runs SET document_json='{' WHERE id=?",
                (dialogue_id,),
            )
        with self.assertRaisesRegex(ValueError, "invalid document JSON"):
            self.store.load(dialogue_id)

    def test_missing_dialogue_fails_cleanly(self):
        with self.assertRaisesRegex(LookupError, "does not exist"):
            self.store.load(999)

    def test_lone_surrogate_payload_round_trips_through_sqlite(self):
        result = DeterministicDialogue().deliberate(
            (SimulationEvent("signal", 0, "set_property", "ape-1", {"value": "\ud800"}),),
            lambda event: GovernorVerdict(True, "accepted"),
        )
        dialogue_id = self.store.record(result)
        stored = self.store.load(dialogue_id)
        self.assertTrue(stored.valid)
        self.assertEqual(stored.result, result)
        row = self.ledger.connection.execute(
            "SELECT document_json FROM dialogue_runs WHERE id=?",
            (dialogue_id,),
        ).fetchone()
        self.assertIn("\\ud800", row[0])


if __name__ == "__main__":
    unittest.main()
