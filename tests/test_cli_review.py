import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from aviary.cli import build_engine, execute_repl_command, parse_repl_command


class CliReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine, self.ledger = build_engine(Path(self.tmp.name) / "aviary.db")

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_argument_free_aliases_require_exact_input(self):
        self.assertEqual(parse_repl_command("help"), ("help", []))
        self.assertEqual(parse_repl_command("quit"), ("quit", []))
        self.assertEqual(parse_repl_command("status"), ("status", []))

    def test_multiword_topics_beginning_with_aliases_are_not_commands(self):
        for topic in (
            "help me choose a database",
            "status of the migration",
            "quit smoking",
            "history of the aviary",
        ):
            with self.subTest(topic=topic):
                self.assertEqual(parse_repl_command(topic), (None, []))

    def test_replay_remains_the_only_bare_command_with_arguments(self):
        self.assertEqual(parse_repl_command("replay 12"), ("replay", ["12"]))
        self.assertEqual(parse_repl_command(":replay 12"), ("replay", ["12"]))

    def test_status_uses_exact_database_count(self):
        for topic in ("one", "two", "three"):
            self.engine.run(topic)
        output = StringIO()
        with redirect_stdout(output):
            execute_repl_command(self.engine, "status", [])
        self.assertIn("Sessions: 3", output.getvalue())

    def test_count_sessions_does_not_call_recent_sessions(self):
        for topic in ("one", "two"):
            self.engine.run(topic)
        self.ledger.recent_sessions = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("status must not materialize session rows")
        )
        output = StringIO()
        with redirect_stdout(output):
            execute_repl_command(self.engine, "status", [])
        self.assertIn("Sessions: 2", output.getvalue())


if __name__ == "__main__":
    unittest.main()
