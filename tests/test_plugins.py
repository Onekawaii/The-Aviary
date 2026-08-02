import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from aviary.cli import build_engine, execute_repl_command, parse_repl_command


class PluginQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "aviary.db"
        self.engine, self.ledger = build_engine(self.db)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_all_builtin_plugins_start_enabled(self):
        states = {item["plugin_id"]: item["enabled"] for item in self.ledger.list_plugins()}
        self.assertEqual(set(states), set(self.engine.registry.ids()))
        self.assertTrue(all(states.values()))

    def test_disabled_plugin_is_quarantined_on_next_launch(self):
        self.ledger.set_plugin_enabled("raven", False)
        self.ledger.close()
        self.engine, self.ledger = build_engine(self.db)
        self.assertNotIn("raven", self.engine.registry.ids())
        self.assertFalse(next(p for p in self.ledger.list_plugins() if p["plugin_id"] == "raven")["enabled"])

    def test_unknown_plugin_change_fails_without_insert(self):
        with self.assertRaises(LookupError):
            self.ledger.set_plugin_enabled("imaginary_bird", False)
        self.assertNotIn("imaginary_bird", {p["plugin_id"] for p in self.ledger.list_plugins()})

    def test_cli_plugin_command_is_not_treated_as_topic(self):
        self.assertEqual(parse_repl_command("plugins disable raven"), ("plugins", ["disable", "raven"]))
        output = StringIO()
        with redirect_stdout(output):
            self.assertTrue(execute_repl_command(self.engine, "plugins", ["disable", "raven"]))
        self.assertIn("restart Aviary to apply", output.getvalue())


if __name__ == "__main__":
    unittest.main()
