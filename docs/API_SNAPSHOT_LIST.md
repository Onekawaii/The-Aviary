# Local Bridge Snapshot List

The Local Bridge exposes read-only, paginated metadata for snapshots in one persisted deterministic simulation receipt.

## Run

```bash
python -m aviary.api --db ledger/aviary.db
```

## Request

```text
GET /api/simulations/{run_id}/snapshots?limit=20&offset=0
```

`run_id` must be a positive SQLite-sized integer.

Pagination parameters are optional:

- `limit` defaults to `20` and must be from `1` through SQLite's signed 64-bit maximum.
- `offset` defaults to `0` and must be from `0` through SQLite's signed 64-bit maximum.
- Each parameter may be supplied at most once.
- Unsupported query parameters are rejected.

## Success response

```json
{
  "run_id": 1,
  "receipt_sha256": "...",
  "receipt_valid": true,
  "count": 1,
  "total_count": 2,
  "limit": 1,
  "offset": 1,
  "snapshots": [
    {
      "tick": 1,
      "state_sha256": "...",
      "valid": true
    }
  ]
}
```

`count` is the number of snapshot metadata records returned on the current page. `total_count` is the number of snapshots in the receipt before pagination. An offset beyond the available snapshots returns HTTP 200 with an empty `snapshots` array and `count: 0`.

The route intentionally omits snapshot state and reconstructed final state. Clients can use a returned tick to request one state through `/api/simulations/{run_id}/snapshots/{tick}`.

`valid` reports whether each stored snapshot state matches its stored SHA-256 digest. `receipt_valid` reports whether the reconstructed receipt hash matches the stored receipt hash. SHA-256 demonstrates internal consistency, not authorship.

## Failure cases

- Invalid run IDs, pagination values, duplicate pagination values, unsupported query parameters, or extra path segments return HTTP 400 with `invalid_request`.
- A missing simulation run returns HTTP 404 with `simulation_not_found`.
- A structurally unreadable receipt returns HTTP 409 with `simulation_invalid`.
- Ledger failures return HTTP 500 with `ledger_unavailable`.
- Reconstructable tampering remains HTTP 200 and is exposed through `valid: false`.

## Known limitations

- Pagination is offset-based and reconstructs the receipt before slicing metadata.
- Read-only route only.
- No detached signature or authorship proof.
- No authentication or TLS; localhost remains the default bind.
- No council, session, scene, event, browser asset, or GUI route is added by this phase.
