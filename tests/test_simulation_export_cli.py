import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from aviary.ledger import SQLiteLedger
from aviary.simulation import DeterministicSimulation, EntityBlueprint, SimulationEvent
from aviary.simulation.export_cli import main
from aviary.simulation.persistence import SimulationReceiptStore


class SimulationExportCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "aviary.db"
        ledger = SQLiteLedger(self.db)
        try:
            result = DeterministicSimulation().replay(
                (EntityBlueprint("raven-1", "bird", {"energy": 2}),),
                (SimulationEvent("gain", 0, "increment_property", "raven-1", {"key": "energy", "amount": 3}),),
            )
            self.run_id = SimulationReceiptStore(ledger).record(result)
        finally:
            ledger.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_exports_full_verified_receipt(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.run_id), "--db", str(self.db)])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["final_state"]["raven-1"]["energy"], 5)
        self.assertEqual(payload["snapshots"][0]["tick"], 0)
        self.assertIn("state_sha256", payload["snapshots"][0])

    def test_tampered_receipt_exports_evidence_and_returns_one(self):
        ledger = SQLiteLedger(self.db)
        try:
            ledger.connection.execute(
                "UPDATE simulation_snapshots SET state_sha256='bad' WHERE run_id=?",
                (self.run_id,),
            )
            ledger.connection.commit()
        finally:
            ledger.close()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.run_id), "--db", str(self.db)])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["snapshot_integrity"], [False])

    def test_missing_run_returns_controlled_error(self):
        error = io.StringIO()
        with redirect_stderr(error):
            code = main(["999", "--db", str(self.db)])
        self.assertEqual(code, 2)
        self.assertIn("does not exist", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
