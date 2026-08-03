from __future__ import annotations

import unittest
from unittest.mock import patch

from aviary.simulation.__main__ import main


class UnifiedSimulationCLITests(unittest.TestCase):
    def test_run_delegates_remaining_arguments(self):
        with patch("aviary.simulation.__main__.run_cli.main", return_value=7) as delegated:
            result = main(["run", "spec.json", "--db", "ledger/test.db", "--json"])
        self.assertEqual(result, 7)
        delegated.assert_called_once_with(["spec.json", "--db", "ledger/test.db", "--json"])

    def test_run_preserves_option_first_arguments(self):
        with patch("aviary.simulation.__main__.run_cli.main", return_value=7) as delegated:
            result = main(["run", "--json", "spec.json"])
        self.assertEqual(result, 7)
        delegated.assert_called_once_with(["--json", "spec.json"])

    def test_list_delegates_remaining_arguments(self):
        with patch("aviary.simulation.__main__.list_cli.main", return_value=5) as delegated:
            result = main(["list", "--limit", "5", "--json"])
        self.assertEqual(result, 5)
        delegated.assert_called_once_with(["--limit", "5", "--json"])

    def test_list_delegates_help(self):
        with patch("aviary.simulation.__main__.list_cli.main", return_value=0) as delegated:
            result = main(["list", "--help"])
        self.assertEqual(result, 0)
        delegated.assert_called_once_with(["--help"])

    def test_verify_delegates_remaining_arguments(self):
        with patch("aviary.simulation.__main__.verify_cli.main", return_value=3) as delegated:
            result = main(["verify", "42", "--json"])
        self.assertEqual(result, 3)
        delegated.assert_called_once_with(["42", "--json"])

    def test_verify_preserves_option_first_arguments(self):
        with patch("aviary.simulation.__main__.verify_cli.main", return_value=3) as delegated:
            result = main(["verify", "--db", "ledger/test.db", "42"])
        self.assertEqual(result, 3)
        delegated.assert_called_once_with(["--db", "ledger/test.db", "42"])

    def test_command_is_required(self):
        with self.assertRaises(SystemExit) as raised:
            main([])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
