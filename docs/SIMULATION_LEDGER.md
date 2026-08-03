# Deterministic Simulation Ledger

## Purpose

Persist deterministic simulation results in the existing SQLite ledger without coupling the simulation kernel to storage, HTTP, rendering, or editor code.

## Source

- `aviary/migrations.py`
- `aviary/simulation/persistence.py`
- `aviary/simulation/cli.py`
- `aviary/simulation/list_cli.py`
- `aviary/simulation/export_cli.py`
- `aviary/simulation/verify_export_cli.py`
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
python -m aviary.simulation export 1 --db ledger/aviary.db --output receipts/run-1.json
python -m aviary.simulation verify 1 --db ledger/aviary.db --json
python -m aviary.simulation verify-export receipts/run-1.json --json
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

## Export CLI

Export a selected run as machine-readable JSON containing the final state, every per-tick snapshot, stored integrity evidence, and recomputed receipt SHA-256:

```bash
python -m aviary.simulation export 1 --db ledger/aviary.db
```

Write the same export to a file using an atomic same-directory replacement:

```bash
python -m aviary.simulation export 1 \
  --db ledger/aviary.db \
  --output receipts/run-1.json
```

The destination directory must already exist. The command writes and flushes a temporary file beside the destination, then replaces the destination only after the complete JSON is durable. A failed write returns exit code `2`, removes the temporary file, and does not emit partial JSON to stdout.

Export returns `0` when all integrity checks pass, `1` when the run loads but integrity fails, and `2` for missing, structurally invalid, or unwritable exports. A tampered run is still exported so its failed integrity evidence can be inspected.

## Export verification CLI

Verify an exported receipt without opening or trusting the SQLite ledger:

```bash
python -m aviary.simulation verify-export receipts/run-1.json
python -m aviary.simulation verify-export receipts/run-1.json --json
```

The verifier reconstructs every snapshot from its JSON state, recomputes every snapshot SHA-256, reconstructs the replay receipt, recomputes its SHA-256, and checks that the export's declared `snapshot_integrity`, `receipt_valid`, and `valid` claims match those recomputed results.

A valid, internally consistent export returns `0`. A well-formed export with changed state, changed hashes, or false integrity claims returns `1`. Invalid JSON, malformed fields, invalid JSON state, or non-increasing snapshot ticks return controlled exit code `2` without a traceback.

This proves internal consistency of the exported artifact. It is not a digital signature and does not prove who created the file; an attacker able to rewrite the complete artifact can recompute its hashes.

## Inspection CLI

Inspect and verify a stored simulation receipt:

```bash
python -m aviary.simulation verify 1 --db ledger/aviary.db
```

Exit codes:

- `0`: the requested operation completed, or the stored/exported receipt verifies.
- `1`: the run or exported artifact loaded but integrity failed.
- `2`: command input, persistence, stored structure, export structure, or output was invalid.

## Verification

```bash
python verify.py
```

Focused tests:

```bash
python -m unittest tests.test_simulation_main_cli tests.test_simulation_list_cli tests.test_simulation_export_cli tests.test_simulation_verify_export_cli tests.test_simulation_persistence tests.test_simulation_cli tests.test_simulation_run_cli -v
```

## Demonstration

A JSON specification is validated, replayed deterministically, persisted, reloaded, and verified before success is reported. Persisted receipt metadata can be paged newest-first, a selected run can be exported with its complete integrity evidence to stdout or an atomically replaced file, and that exported file can be verified independently without ledger access.

## Failure cases

- Omitting the `run`, `list`, `export`, `verify`, or `verify-export` command returns argparse exit code `2`.
- Invalid JSON and missing required specification fields return exit code `2` without a traceback.
- Events targeting absent entities are rejected before replay.
- Listing with `--limit 0` or a negative offset returns exit code `2` without a traceback.
- Missing run IDs return CLI exit code `2`.
- Changed snapshot state is exported with `valid: false` and returns exit code `1`.
- An unwritable or invalid `--output` destination returns exit code `2`, leaves no temporary file, and does not replace the existing destination.
- A changed exported snapshot, digest, or integrity claim returns exit code `1`.
- Malformed export JSON or duplicate/out-of-order snapshot ticks return exit code `2` without a traceback.

## Known limitations

- Listing reads receipt metadata only and does not verify snapshot integrity.
- Export does not create missing destination directories.
- Export verification proves artifact consistency, not authenticity; hashes are not signatures.
- JSON specifications can use only effects registered by the built-in deterministic simulation engine.
- Stored runs are not yet attached to council sessions or Arkheopantheochive scenes.
- The database stores snapshots as canonical JSON rather than compressed blobs.
- There is no HTTP bridge, renderer, editor, or GUI in this phase.
- Custom simulation effects remain trusted Python callables and cannot be loaded from JSON.
