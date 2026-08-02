# Deterministic Simulation Ledger

## Purpose

Persist deterministic simulation results in the existing SQLite ledger without coupling the simulation kernel to storage, HTTP, rendering, or editor code.

## Source

- `aviary/migrations.py`
- `aviary/simulation/persistence.py`
- `aviary/simulation/cli.py`
- `aviary/simulation/__init__.py`

## Storage contract

Migration 3 adds:

- `simulation_runs` for the final state, snapshot count, and replay receipt hash.
- `simulation_snapshots` for ordered per-tick state and SHA-256 hashes.
- `simulation.recorded` history events.

`SimulationReceiptStore.record()` is idempotent for an already verified receipt. `load()` rebuilds every snapshot and the final replay result, recomputes their hashes, and returns explicit integrity status.

## CLI

Inspect and verify a stored simulation receipt:

```bash
python -m aviary.simulation.cli 1 --db ledger/aviary.db
```

Machine-readable output:

```bash
python -m aviary.simulation.cli 1 --db ledger/aviary.db --json
```

Exit codes:

- `0`: the stored receipt and all snapshots verify.
- `1`: the run loaded but integrity failed.
- `2`: the run was missing or structurally invalid.

## Verification

```bash
python verify.py
```

Focused tests:

```bash
python -m unittest tests.test_simulation_persistence tests.test_simulation_cli -v
```

## Demonstration

Run a deterministic simulation, store the result, reopen it by numeric run ID, and confirm:

- the rebuilt result equals the original result;
- every snapshot hash is valid;
- the rebuilt replay receipt equals the stored receipt;
- recording the same verified receipt again returns the original run ID;
- the CLI reports integrity in human-readable or JSON form.

## Failure cases

- Missing run IDs raise `LookupError` in the API and return CLI exit code `2`.
- Snapshot-count drift raises `ValueError`.
- Changed snapshot state returns `valid == False` and CLI exit code `1`.
- Duplicate verified receipts do not create duplicate rows.
- Duplicate receipts whose stored data no longer verifies are rejected.

## Known limitations

- The CLI verifies and displays existing runs; it does not author simulations.
- Stored runs are not yet attached to council sessions or Arkheopantheochive scenes.
- The database stores snapshots as canonical JSON rather than compressed blobs.
- There is no HTTP bridge, renderer, editor, or GUI in this phase.
- Custom simulation effects remain trusted Python callables.
