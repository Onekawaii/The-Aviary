import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from aviary.cli import build_engine, execute_repl_command, parse_repl_command


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine, self.ledger = build_engine(Path(self.tmp.name) / "cli.db")

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def capture(self, command, args=None):
        stream = io.StringIO()
        with redirect_stdout(stream):
            keep_running = execute_repl_command(self.engine, command, args or [])
        return keep_running, stream.getvalue()

    def test_bare_and_colon_aliases_match(self):
        pairs = (
            ("birds", ":birds", "birds"),
            ("history", ":history", "history"),
            ("help", ":help", "help"),
            ("status", ":status", "status"),
            ("schema", ":schema", "schema"),
            ("quit", ":quit", "quit"),
        )
        for bare, colon, expected in pairs:
            with self.subTest(command=bare):
                self.assertEqual(parse_repl_command(bare)[0], expected)
                self.assertEqual(parse_repl_command(colon)[0], expected)

    def test_replay_alias_accepts_session_id(self):
        self.assertEqual(parse_repl_command("replay 17"), ("replay", ["17"]))
        self.assertEqual(parse_repl_command(":replay 17"), ("replay", ["17"]))

    def test_unknown_text_remains_a_topic(self):
        self.assertEqual(parse_repl_command("build a local AI"), (None, []))

    def test_replay_without_id_returns_usage(self):
        keep_running, output = self.capture("replay")
        self.assertTrue(keep_running)
        self.assertIn("Usage: replay <session-id>", output)

    def test_status_and_schema_report_runtime(self):
        _, status = self.capture("status")
        _, schema = self.capture("schema")
        self.assertIn("Version:", status)
        self.assertIn("Database:", status)
        self.assertIn("Birds: 6", status)
        self.assertIn("Ledger schema version:", schema)

    def test_quit_stops_repl(self):
        keep_running, _ = self.capture("quit")
        self.assertFalse(keep_running)


if __name__ == "__main__":
    unittest.main()
