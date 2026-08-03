# Deterministic Simulation Ledger

## Purpose

Persist deterministic simulation results in the existing SQLite ledger without coupling the simulation kernel to storage, HTTP, rendering, or editor code.

## Source

- `aviary/migrations.py`
- `aviary/simulation/persistence.py`
- `aviary/simulation/cli.py`
- `aviary/simulation/list_cli.py`
- `aviary/simulation/run_cli.py`
- `aviary/simulation/__main__.py`
- `aviary/simulation/__init__.py`

## Storage contract

Migration 3 adds:

- `simulation_runs` for the final state, snapshot count, and replay receipt hash.
- `simulation_snapshots` for ordered per-tick state and SHA-256 hashes.
- `simulation.recorded` history events.

`SimulationReceiptStore.record()` is idempotent for an already verified receipt. `load()` rebuilds every snapshot and the final replay result, recomputes their hashes, and returns explicit integrity status. `list_runs()` returns newest-first receipt metadata without loading snapshot bodies.

## Unified CLI

The preferred terminal entry point is:

```bash
python -m aviary.simulation run simulation.json --db ledger/aviary.db --json
python -m aviary.simulation list --db ledger/aviary.db --limit 20 --json
python -m aviary.simulation verify 1 --db ledger/aviary.db --json
```

The older module-specific entry points remain compatible.

## Authoring CLI

Create `simulation.json`:

```json
{
  "blueprints": [
    {"entity_id": "raven-1", "kind": "bird", "state": {"energy": 2}}
  ],
  "events": [
    {"event_id": "gain", "tick": 0, "kind": "increment_property", "target_id": "raven-1", "payload": {"key": "energy", "amount": 3}}
  ]
}
```

Run, persist, reload, and verify it:

```bash
python -m aviary.simulation run simulation.json --db ledger/aviary.db
```

## Listing CLI

List stored receipt metadata newest-first:

```bash
python -m aviary.simulation list --db ledger/aviary.db --limit 20 --offset 0
```

The listing reports run ID, creation timestamp, snapshot count, and receipt SHA-256. It deliberately does not claim integrity verification; use `verify` for that.

## Inspection CLI

Inspect and verify a stored simulation receipt:

```bash
python -m aviary.simulation verify 1 --db ledger/aviary.db
```

Exit codes:

- `0`: the requested operation completed, or the stored receipt verifies.
- `1`: the run loaded but integrity failed.
- `2`: command input, persistence, or stored structure was invalid.

## Verification

```bash
python verify.py
```

Focused tests:

```bash
python -m unittest tests.test_simulation_main_cli tests.test_simulation_list_cli tests.test_simulation_persistence tests.test_simulation_cli tests.test_simulation_run_cli -v
```

## Demonstration

A JSON specification is validated, replayed deterministically, persisted, reloaded, and verified before success is reported. Persisted receipt metadata can be paged newest-first and a selected numeric run ID can then be verified independently through the same unified CLI.

## Failure cases

- Omitting the `run`, `list`, or `verify` command returns argparse exit code `2`.
- Invalid JSON and missing required specification fields return exit code `2` without a traceback.
- Events targeting absent entities are rejected before replay.
- Listing with `--limit 0` or a negative offset returns exit code `2` without a traceback.
- Missing run IDs return CLI exit code `2`.
- Changed snapshot state returns exit code `1`.

## Known limitations

- Listing reads receipt metadata only and does not verify snapshot integrity.
- JSON specifications can use only effects registered by the built-in deterministic simulation engine.
- Stored runs are not yet attached to council sessions or Arkheopantheochive scenes.
- The database stores snapshots as canonical JSON rather than compressed blobs.
- There is no HTTP bridge, renderer, editor, or GUI in this phase.
- Custom simulation effects remain trusted Python callables and cannot be loaded from JSON.
