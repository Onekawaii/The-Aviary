from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from aviary.simulation.contracts import ReplayResult, SimulationSnapshot
from aviary.simulation.verify_export_cli import main


class SimulationVerifyExportCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "receipt.json"
        snapshot = SimulationSnapshot.create(0, {"raven-1": {"energy": 5}})
        result = ReplayResult.create((snapshot,), {"raven-1": {"energy": 5}})
        self.payload = {
            "run_id": 7,
            "valid": True,
            "receipt_valid": True,
            "receipt_sha256": result.receipt_hash,
            "snapshot_integrity": [True],
            "snapshots": [
                {
                    "tick": snapshot.tick,
                    "state": {"raven-1": {"energy": 5}},
                    "state_sha256": snapshot.state_hash,
                }
            ],
            "final_state": {"raven-1": {"energy": 5}},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def write_payload(self) -> None:
        self.path.write_text(json.dumps(self.payload), encoding="utf-8")

    def test_verifies_export_without_ledger_access(self):
        self.write_payload()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.path), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(result["valid"])
        self.assertTrue(result["receipt_valid"])
        self.assertTrue(result["claims_match"])
        self.assertEqual(result["snapshot_integrity"], [True])

    def test_tampered_snapshot_returns_integrity_failure(self):
        self.payload["snapshots"][0]["state"]["raven-1"]["energy"] = 99
        self.write_payload()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.path), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(result["valid"])
        self.assertFalse(result["receipt_valid"])
        self.assertEqual(result["snapshot_integrity"], [False])

    def test_false_integrity_claim_returns_failure(self):
        self.payload["valid"] = False
        self.write_payload()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.path), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(result["valid"])
        self.assertTrue(result["receipt_valid"])
        self.assertFalse(result["claims_match"])

    def test_invalid_snapshot_order_returns_controlled_error(self):
        duplicate = dict(self.payload["snapshots"][0])
        self.payload["snapshots"].append(duplicate)
        self.payload["snapshot_integrity"].append(True)
        self.write_payload()
        error = io.StringIO()
        with redirect_stderr(error):
            code = main([str(self.path)])
        self.assertEqual(code, 2)
        self.assertIn("strictly increasing", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())

    def test_malformed_json_returns_controlled_error(self):
        self.path.write_text("{not-json", encoding="utf-8")
        error = io.StringIO()
        with redirect_stderr(error):
            code = main([str(self.path)])
        self.assertEqual(code, 2)
        self.assertIn("ERROR:", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
