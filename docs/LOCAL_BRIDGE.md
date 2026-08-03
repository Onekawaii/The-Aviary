# Aviary Local Bridge

## Purpose

Expose existing Aviary contracts to local clients without moving reasoning into the browser.

The bridge remains read-only.

## Run

```bash
python -m aviary.api
```

Default address:

```text
http://127.0.0.1:8787
```

Custom bind and ledger:

```bash
python -m aviary.api --host 127.0.0.1 --port 8080 --db ledger/aviary.db
```

## Endpoints

### `GET /api/health`

Reports bridge status, API version, and discovered bird count.

### `GET /api/birds`

Returns each discovered bird's ID, module, metadata, voice, and JSON schema.

### `GET /api/simulations`

Lists persisted simulation receipt summaries newest-first.

Optional pagination:

```text
/api/simulations?limit=20&offset=0
```

Each entry contains the run ID, receipt SHA-256, snapshot count, and creation timestamp. The endpoint lists metadata only; it does not claim receipt integrity verification.

## Verification

```bash
python verify.py
```

Focused:

```bash
python -m unittest tests.test_api_bridge -v
```

## Demonstration

Start the bridge and open:

```text
http://127.0.0.1:8787/api/health
http://127.0.0.1:8787/api/birds
http://127.0.0.1:8787/api/simulations?limit=5&offset=0
```

## Failure cases

- Invalid pagination or unsupported query parameters return structured HTTP 400 JSON.
- Ledger or migration failures return structured HTTP 500 JSON without a traceback.
- Unknown paths return structured HTTP 404 JSON.
- POST requests return structured HTTP 405 JSON and execute nothing.
- Empty hosts and invalid ports fail before binding.
- Bind failures return controlled CLI exit code 2.

## Known limitations

- Read-only endpoints only.
- Listing simulation metadata does not verify receipt integrity.
- No council analysis, session, replay-detail, scene, or event routes yet.
- No authentication or TLS; the bridge binds to localhost by default.
- No browser assets or GUI are included.
