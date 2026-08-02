# Ledger Migration Protocol

The Aviary uses ordered, immutable SQLite migrations from `aviary/migrations.py`.

## Contract

1. Migration versions are contiguous integers beginning at `1`.
2. Applied migrations are recorded in `schema_migrations` with name, SHA-256 checksum, and UTC timestamp.
3. Existing migration definitions are immutable. Editing an applied migration causes startup to fail with `migration drift detected`.
4. Each pending migration runs inside an explicit SQLite `BEGIN IMMEDIATE` transaction.
5. A failed statement triggers `ROLLBACK`; neither partial schema changes nor a migration receipt may survive.
6. New schema work is appended as a new migration. Old migrations are never rewritten.

## Demonstration

```bash
python - <<'PY'
from aviary.ledger import SQLiteLedger
ledger = SQLiteLedger("aviary.db")
print("schema version:", ledger.get_schema_version())
for row in ledger.connection.execute(
    "SELECT version,name,checksum,applied_at FROM schema_migrations ORDER BY version"
):
    print(dict(row))
ledger.close()
PY
```

A fresh or pre-migration v0 database advances to the latest version when `SQLiteLedger` opens. Existing rows remain intact because the foundation migration uses idempotent `CREATE TABLE IF NOT EXISTS` statements.

## Verification

```bash
python verify.py
```

Migration tests cover:

- fresh database installation;
- v0 database adoption without deleting existing topic data;
- SHA-256 drift rejection;
- rollback of both DDL and migration receipt after an invalid statement.

## Failure case

A changed checksum, renamed historical migration, invalid SQL statement, or non-contiguous migration sequence closes the sanctuary by raising an exception before normal ledger use.

## Known limitations

- The v0 adoption path confirms migration execution and preserves existing rows, but it does not deeply fingerprint every legacy column definition.
- Migrations are forward-only. Automated downgrade migrations are intentionally not implemented.
- `BEGIN IMMEDIATE` takes a write reservation while migrating; another writer may briefly block startup.
