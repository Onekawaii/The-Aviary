# Deterministic Simulation Ledger

## Purpose

Persist deterministic simulation results in the existing SQLite ledger without coupling the simulation kernel to storage, HTTP, rendering, or editor code.

## Source

- `aviary/migrations.py`
- `aviary/simulation/persistence.py`
- `aviary/simulation/cli.py`
- `aviary/simulation/run_cli.py`
- `aviary/simulation/__init__.py`

## Storage contract

Migration 3 adds:

- `simulation_runs` for the final state, snapshot count, and replay receipt hash.
- `simulation_snapshots` for ordered per-tick state and SHA-256 hashes.
- `simulation.recorded` history events.

`SimulationReceiptStore.record()` is idempotent for an already verified receipt. `load()` rebuilds every snapshot and the final replay result, recomputes their hashes, and returns explicit integrity status.

## Authoring CLI

Create `simulation.json`:

```json
{
  "blueprints": [
    {
      "entity_id": "raven-1",
      "kind": "bird",
      "state": {"energy": 2}
    }
  ],
  "events": [
    {
      "event_id": "gain",
      "tick": 0,
      "kind": "increment_property",
      "target_id": "raven-1",
      "payload": {"key": "energy", "amount": 3}
    }
  ]
}
```

Run, persist, reload, and verify it:

```bash
python -m aviary.simulation.run_cli simulation.json --db ledger/aviary.db
```

Machine-readable output:

```bash
python -m aviary.simulation.run_cli simulation.json --db ledger/aviary.db --json
```

## Inspection CLI

Inspect and verify a stored simulation receipt:

```bash
python -m aviary.simulation.cli 1 --db ledger/aviary.db
```

Machine-readable output:

```bash
python -m aviary.simulation.cli 1 --db ledger/aviary.db --json
```

Exit codes for both CLIs:

- `0`: the simulation was persisted and verified, or the stored receipt verifies.
- `1`: the run loaded but integrity failed.
- `2`: input, persistence, or stored structure was invalid.

## Verification

```bash
python verify.py
```

Focused tests:

```bash
python -m unittest tests.test_simulation_persistence tests.test_simulation_cli tests.test_simulation_run_cli -v
```

## Demonstration

A JSON specification is validated, replayed deterministically, persisted, reloaded, and verified before success is reported. The resulting numeric run ID can then be inspected independently with `aviary.simulation.cli`.

The receipts demonstrate:

- the rebuilt result equals the original result;
- every snapshot hash is valid;
- the rebuilt replay receipt equals the stored receipt;
- recording the same verified receipt again returns the original run ID;
- both CLIs report integrity in human-readable or JSON form.

## Failure cases

- Invalid JSON and missing required specification fields return exit code `2` without a traceback.
- Events targeting absent entities are rejected before replay.
- Missing run IDs raise `LookupError` in the API and return CLI exit code `2`.
- Snapshot-count drift raises `ValueError`.
- Changed snapshot state returns `valid == False` and CLI exit code `1`.
- Duplicate verified receipts do not create duplicate rows.
- Duplicate receipts whose stored data no longer verifies are rejected.

## Known limitations

- JSON specifications can use only effects registered by the built-in deterministic simulation engine.
- Stored runs are not yet attached to council sessions or Arkheopantheochive scenes.
- The database stores snapshots as canonical JSON rather than compressed blobs.
- There is no HTTP bridge, renderer, editor, or GUI in this phase.
- Custom simulation effects remain trusted Python callables and cannot be loaded from JSON.
