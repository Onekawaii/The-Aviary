from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

from aviary.simulation.list_cli import main
from aviary.simulation.persistence import SimulationReceiptStore


class SimulationListTests(unittest.TestCase):
    def test_store_lists_newest_runs_first(self):
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = [
            {"id": 3, "receipt_sha256": "c" * 64, "snapshot_count": 2, "created_at": "2026-08-03T00:00:00Z"},
            {"id": 2, "receipt_sha256": "b" * 64, "snapshot_count": 1, "created_at": "2026-08-02T00:00:00Z"},
        ]
        ledger = MagicMock(connection=connection)
        runs = SimulationReceiptStore(ledger).list_runs(limit=2, offset=1)
        self.assertEqual([run.run_id for run in runs], [3, 2])
        connection.execute.assert_called_once_with(
            "SELECT id,receipt_sha256,snapshot_count,created_at FROM simulation_runs ORDER BY id DESC LIMIT ? OFFSET ?",
            (2, 1),
        )

    def test_store_rejects_invalid_page_values(self):
        store = SimulationReceiptStore(MagicMock())
        with self.assertRaisesRegex(ValueError, "limit"):
            store.list_runs(limit=0)
        with self.assertRaisesRegex(ValueError, "offset"):
            store.list_runs(offset=-1)

    @patch("aviary.simulation.list_cli.SQLiteLedger")
    def test_cli_reports_empty_json_list(self, ledger_type):
        ledger = ledger_type.return_value
        with patch.object(SimulationReceiptStore, "list_runs", return_value=()):
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(["--json"])
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), "[]")
        ledger.close.assert_called_once_with()

    @patch("aviary.simulation.list_cli.SQLiteLedger")
    def test_cli_rejects_invalid_limit_without_traceback(self, ledger_type):
        error = io.StringIO()
        with redirect_stderr(error):
            result = main(["--limit", "0"])
        self.assertEqual(result, 2)
        self.assertIn("limit must be at least 1", error.getvalue())
        ledger_type.return_value.close.assert_called_once_with()

    @patch("aviary.simulation.list_cli.SQLiteLedger", side_effect=RuntimeError("migration drift"))
    def test_cli_reports_migration_failure_without_traceback(self, ledger_type):
        error = io.StringIO()
        with redirect_stderr(error):
            result = main(["--json"])
        self.assertEqual(result, 2)
        self.assertIn("ERROR: migration drift", error.getvalue())
        ledger_type.assert_called_once()


if __name__ == "__main__":
    unittest.main()
