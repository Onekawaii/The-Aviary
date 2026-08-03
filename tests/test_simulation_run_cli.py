import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from aviary.ledger import SQLiteLedger
from aviary.simulation.persistence import SimulationReceiptStore
from aviary.simulation.run_cli import main


class SimulationRunCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "aviary.db"
        self.spec = self.root / "simulation.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, payload):
        self.spec.write_text(json.dumps(payload), encoding="utf-8")

    def test_runs_records_and_verifies_json_spec(self):
        self._write(
            {
                "blueprints": [
                    {"entity_id": "raven-1", "kind": "bird", "state": {"energy": 2}}
                ],
                "events": [
                    {
                        "event_id": "gain",
                        "tick": 0,
                        "kind": "increment_property",
                        "target_id": "raven-1",
                        "payload": {"key": "energy", "amount": 3},
                    }
                ],
            }
        )
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([str(self.spec), "--db", str(self.db), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["snapshot_count"], 1)

        ledger = SQLiteLedger(self.db)
        try:
            stored = SimulationReceiptStore(ledger).load(payload["run_id"])
            self.assertEqual(stored.result.final_state["raven-1"]["energy"], 5)
        finally:
            ledger.close()

    def test_repeated_spec_is_idempotent(self):
        self._write(
            {
                "blueprints": [
                    {"entity_id": "raven-1", "kind": "bird", "state": {"energy": 2}}
                ],
                "events": [],
            }
        )
        first = io.StringIO()
        second = io.StringIO()
        with redirect_stdout(first):
            self.assertEqual(main([str(self.spec), "--db", str(self.db), "--json"]), 0)
        with redirect_stdout(second):
            self.assertEqual(main([str(self.spec), "--db", str(self.db), "--json"]), 0)
        self.assertEqual(json.loads(first.getvalue())["run_id"], json.loads(second.getvalue())["run_id"])

    def test_invalid_json_returns_controlled_error(self):
        self.spec.write_text("{not json", encoding="utf-8")
        error = io.StringIO()
        with redirect_stderr(error):
            code = main([str(self.spec), "--db", str(self.db)])
        self.assertEqual(code, 2)
        self.assertIn("invalid JSON", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())

    def test_missing_required_field_returns_controlled_error(self):
        self._write({"blueprints": [{"kind": "bird"}], "events": []})
        error = io.StringIO()
        with redirect_stderr(error):
            code = main([str(self.spec), "--db", str(self.db)])
        self.assertEqual(code, 2)
        self.assertIn("missing 'entity_id'", error.getvalue())

    def test_missing_target_returns_controlled_error(self):
        self._write(
            {
                "blueprints": [],
                "events": [
                    {
                        "event_id": "gain",
                        "tick": 0,
                        "kind": "increment_property",
                        "target_id": "missing",
                        "payload": {"key": "energy"},
                    }
                ],
            }
        )
        error = io.StringIO()
        with redirect_stderr(error):
            code = main([str(self.spec), "--db", str(self.db)])
        self.assertEqual(code, 2)
        self.assertIn("unknown entity", error.getvalue())


if __name__ == "__main__":
    unittest.main()
