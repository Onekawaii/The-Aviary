import sqlite3
import tempfile
import unittest
from pathlib import Path

from aviary.ledger import SQLiteLedger
from aviary.migrations import MIGRATIONS, Migration, apply_migrations, current_schema_version


class MigrationTests(unittest.TestCase):
    def test_fresh_database_reaches_latest_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = SQLiteLedger(Path(tmp) / "fresh.db")
            try:
                self.assertEqual(ledger.schema_version, len(MIGRATIONS))
                self.assertEqual(ledger.get_schema_version(), len(MIGRATIONS))
                rows = ledger.connection.execute(
                    "SELECT version,name,checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
                self.assertEqual([row["version"] for row in rows], [1, 2])
                self.assertTrue(all(len(row["checksum"]) == 64 for row in rows))
            finally:
                ledger.close()

    def test_existing_v0_database_is_adopted_without_data_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.db"
            connection = sqlite3.connect(path)
            connection.execute(
                "CREATE TABLE topics(id INTEGER PRIMARY KEY,text TEXT NOT NULL,context_json TEXT NOT NULL,created_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO topics(text,context_json,created_at) VALUES('legacy','{}','before-migrations')"
            )
            connection.commit()
            connection.close()

            ledger = SQLiteLedger(path)
            try:
                row = ledger.connection.execute("SELECT text FROM topics WHERE id=1").fetchone()
                self.assertEqual(row["text"], "legacy")
                self.assertEqual(ledger.get_schema_version(), len(MIGRATIONS))
            finally:
                ledger.close()

    def test_checksum_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "drift.db"
            ledger = SQLiteLedger(path)
            with ledger.connection:
                ledger.connection.execute(
                    "UPDATE schema_migrations SET checksum='tampered' WHERE version=1"
                )
            ledger.close()

            with self.assertRaisesRegex(RuntimeError, "migration drift detected"):
                SQLiteLedger(path)

    def test_failed_migration_rolls_back_schema_and_receipt(self):
        connection = sqlite3.connect(":memory:")
        bad = Migration(
            1,
            "broken",
            (
                "CREATE TABLE should_not_survive(id INTEGER PRIMARY KEY)",
                "THIS IS NOT VALID SQL",
            ),
        )
        with self.assertRaisesRegex(RuntimeError, "failed and was rolled back"):
            apply_migrations(connection, (bad,))

        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='should_not_survive'"
        ).fetchone()
        receipt = connection.execute(
            "SELECT version FROM schema_migrations WHERE version=1"
        ).fetchone()
        self.assertIsNone(table)
        self.assertIsNone(receipt)
        self.assertEqual(current_schema_version(connection), 0)
        connection.close()


if __name__ == "__main__":
    unittest.main()
