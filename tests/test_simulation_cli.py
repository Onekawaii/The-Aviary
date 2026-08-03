import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from aviary.ledger import SQLiteLedger
from aviary.simulation import DeterministicSimulation, EntityBlueprint, SimulationEvent
from aviary.simulation.cli import main
from aviary.simulation.persistence import SimulationReceiptStore


class SimulationCLITests(unittest.TestCase):
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

    def test_human_output_verifies_receipt(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.run_id), "--db", str(self.db)])
        self.assertEqual(code, 0)
        self.assertIn("Integrity: PASS", output.getvalue())
        self.assertIn("Receipt: sha256:", output.getvalue())

    def test_json_output_is_machine_readable(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.run_id), "--db", str(self.db), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["final_state"]["raven-1"]["energy"], 5)

    def test_missing_run_returns_controlled_error(self):
        error = io.StringIO()
        with redirect_stderr(error):
            code = main(["999", "--db", str(self.db)])
        self.assertEqual(code, 2)
        self.assertIn("does not exist", error.getvalue())

    def test_oversized_run_id_returns_controlled_error(self):
        error = io.StringIO()
        with redirect_stderr(error):
            code = main([str(2**63), "--db", str(self.db)])
        self.assertEqual(code, 2)
        self.assertIn("ERROR:", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
