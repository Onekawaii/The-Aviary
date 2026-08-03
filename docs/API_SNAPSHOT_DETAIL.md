# Local Bridge Snapshot Detail

The Local Bridge exposes one read-only snapshot from a persisted deterministic simulation receipt.

## Run

```bash
python -m aviary.api --db ledger/aviary.db
```

## Request

```text
GET /api/simulations/{run_id}/snapshots/{tick}
```

`run_id` must be a positive SQLite-sized integer. `tick` must be a non-negative SQLite-sized integer. Query parameters are rejected.

## Success response

```json
{
  "run_id": 1,
  "receipt_sha256": "...",
  "receipt_valid": true,
  "tick": 1,
  "state": {"owl-1": {"energy": 5}},
  "state_sha256": "...",
  "valid": true
}
```

The route returns only the requested timeline point. It does not include the full snapshot list or reconstructed final state.

`valid` reports whether the stored snapshot state matches its stored SHA-256 digest. `receipt_valid` reports whether the reconstructed receipt hash matches the stored receipt hash. SHA-256 demonstrates internal consistency, not authorship.

## Failure cases

- Invalid run IDs, ticks, extra path segments, or query parameters return HTTP 400 with `invalid_request`.
- A missing simulation run returns HTTP 404 with `simulation_not_found`.
- An existing run without the requested tick returns HTTP 404 with `snapshot_not_found`.
- A structurally unreadable receipt returns HTTP 409 with `simulation_invalid`.
- Ledger failures return HTTP 500 with `ledger_unavailable`.
- A reconstructable but tampered snapshot remains HTTP 200 with `valid: false`; evidence is not hidden.

## Known limitations

- Read-only route only.
- No detached signature or authorship proof.
- No authentication or TLS; localhost remains the default bind.
- No council, session, scene, event, browser asset, or GUI route is added by this phase.
