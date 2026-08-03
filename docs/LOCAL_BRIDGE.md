# Aviary Local Bridge

## Purpose

Expose existing Aviary contracts to local clients without moving reasoning into the browser. The bridge remains read-only.

## Run

```bash
python -m aviary.api
```

Default address: `http://127.0.0.1:8787`

The bridge uses the same ledger resolution as the main CLI. Set `AVIARY_DB` or pass `--db` explicitly. Ledger initialization and migrations complete before threaded request handling begins.

## Endpoints

### `GET /api/health`

Reports bridge status, API version, and discovered bird count.

### `GET /api/birds`

Returns discovered bird contracts.

### `GET /api/simulations`

Lists persisted simulation receipt summaries newest-first.

```text
/api/simulations?limit=20&offset=0
```

Listing metadata does not claim integrity verification.

### `GET /api/simulations/{run_id}`

Loads one persisted receipt, reconstructs every snapshot and final state, recomputes receipt integrity, and returns:

- `receipt_sha256`
- `receipt_valid`
- per-snapshot `state_sha256` and `valid`
- aggregate `valid`
- reconstructed snapshots and final state

A valid HTTP response can intentionally contain `"valid": false` when stored evidence was tampered with.

## Verification

```bash
python verify.py
python -m unittest tests.test_api_bridge -v
```

## Demonstration

```text
GET http://127.0.0.1:8787/api/health
GET http://127.0.0.1:8787/api/birds
GET http://127.0.0.1:8787/api/simulations?limit=5&offset=0
GET http://127.0.0.1:8787/api/simulations/1
```

## Failure cases

- Invalid pagination, invalid run IDs, out-of-range integers, and unsupported query parameters return structured HTTP 400 JSON.
- Missing runs return structured HTTP 404 JSON.
- Structurally unreadable receipts return structured HTTP 409 JSON.
- Ledger or migration failures stop startup with controlled CLI exit code 2.
- Runtime ledger failures return structured HTTP 500 JSON without a traceback.
- Unknown paths return structured HTTP 404 JSON.
- POST requests return structured HTTP 405 JSON and execute nothing.

## Known limitations

- Read-only endpoints only.
- No detached artifact signature or authorship proof.
- No council analysis, session, scene, or event routes yet.
- No authentication or TLS; localhost is the default bind.
- No browser assets or GUI are included.
