# Local Bridge Snapshot List

The Local Bridge exposes read-only metadata for every snapshot in one persisted deterministic simulation receipt.

## Run

```bash
python -m aviary.api --db ledger/aviary.db
```

## Request

```text
GET /api/simulations/{run_id}/snapshots
```

`run_id` must be a positive SQLite-sized integer. Query parameters are rejected.

## Success response

```json
{
  "run_id": 1,
  "receipt_sha256": "...",
  "receipt_valid": true,
  "count": 2,
  "snapshots": [
    {
      "tick": 0,
      "state_sha256": "...",
      "valid": true
    },
    {
      "tick": 1,
      "state_sha256": "...",
      "valid": true
    }
  ]
}
```

The route intentionally omits snapshot state and reconstructed final state. Clients can use the tick list to request one state through `/api/simulations/{run_id}/snapshots/{tick}`.

`valid` reports whether each stored snapshot state matches its stored SHA-256 digest. `receipt_valid` reports whether the reconstructed receipt hash matches the stored receipt hash. SHA-256 demonstrates internal consistency, not authorship.

## Failure cases

- Invalid run IDs, extra path segments, or query parameters return HTTP 400 with `invalid_request`.
- A missing simulation run returns HTTP 404 with `simulation_not_found`.
- A structurally unreadable receipt returns HTTP 409 with `simulation_invalid`.
- Ledger failures return HTTP 500 with `ledger_unavailable`.
- Reconstructable tampering remains HTTP 200 and is exposed through `valid: false`.

## Known limitations

- The response is not paginated; one run returns all snapshot metadata.
- Read-only route only.
- No detached signature or authorship proof.
- No authentication or TLS; localhost remains the default bind.
- No council, session, scene, event, browser asset, or GUI route is added by this phase.
