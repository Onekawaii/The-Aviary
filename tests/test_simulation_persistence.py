from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aviary.ledger import SQLiteLedger
from aviary.simulation import DeterministicSimulation, EntityBlueprint, SimulationEvent
from aviary.simulation.persistence import SimulationReceiptStore


class SimulationPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.ledger = SQLiteLedger(Path(self.tempdir.name) / "aviary.db")
        self.store = SimulationReceiptStore(self.ledger)
        self.result = DeterministicSimulation().replay(
            (EntityBlueprint("owl-1", "bird", {"energy": 3}),),
            (
                SimulationEvent(
                    "rise",
                    1,
                    "increment_property",
                    "owl-1",
                    {"key": "energy", "amount": 2},
                ),
            ),
        )

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def test_schema_migrates_to_simulation_receipts(self):
        self.assertEqual(self.ledger.get_schema_version(), 3)

    def test_record_and_load_preserve_verified_receipt(self):
        run_id = self.store.record(self.result)
        stored = self.store.load(run_id)
        self.assertTrue(stored.valid)
        self.assertEqual(stored.result, self.result)
        self.assertEqual(stored.result.receipt_hash, self.result.receipt_hash)

    def test_record_is_idempotent_for_same_receipt(self):
        first = self.store.record(self.result)
        second = self.store.record(self.result)
        self.assertEqual(first, second)
        row = self.ledger.connection.execute(
            "SELECT COUNT(*) FROM simulation_runs"
        ).fetchone()
        self.assertEqual(int(row[0]), 1)

    def test_lone_surrogate_state_round_trips_through_sqlite(self):
        result = DeterministicSimulation().replay(
            (EntityBlueprint("owl-1", "bird", {"signal": "\ud800"}),),
            (),
        )
        run_id = self.store.record(result)
        stored = self.store.load(run_id)
        self.assertTrue(stored.valid)
        self.assertEqual(stored.result, result)
        row = self.ledger.connection.execute(
            "SELECT final_state_json FROM simulation_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        self.assertIn("\\ud800", row[0])

    def test_tampered_snapshot_is_reported_invalid(self):
        run_id = self.store.record(self.result)
        with self.ledger.connection:
            self.ledger.connection.execute(
                "UPDATE simulation_snapshots SET state_json=? WHERE run_id=? AND tick=0",
                ('{"owl-1":{"energy":99}}', run_id),
            )
        stored = self.store.load(run_id)
        self.assertFalse(stored.valid)
        self.assertFalse(stored.snapshot_integrity[0])

    def test_missing_run_fails_cleanly(self):
        with self.assertRaisesRegex(LookupError, "does not exist"):
            self.store.load(999)

    def test_snapshot_count_tampering_fails_cleanly(self):
        run_id = self.store.record(self.result)
        with self.ledger.connection:
            self.ledger.connection.execute(
                "UPDATE simulation_runs SET snapshot_count=99 WHERE id=?",
                (run_id,),
            )
        with self.assertRaisesRegex(ValueError, "snapshot count"):
            self.store.load(run_id)


if __name__ == "__main__":
    unittest.main()
