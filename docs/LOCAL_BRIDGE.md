# Aviary Local Bridge

## Purpose

Expose the existing Aviary contracts to local clients without moving reasoning into the browser.

This first slice is intentionally read-only.

## Run

```bash
python -m aviary.api
```

Default address:

```text
http://127.0.0.1:8787
```

Custom bind:

```bash
python -m aviary.api --host 127.0.0.1 --port 8080
```

## Endpoints

### `GET /api/health`

Reports bridge status, API version, and discovered bird count.

### `GET /api/birds`

Returns each discovered bird's ID, module, metadata, voice, and JSON schema.

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
```

Both responses are deterministic JSON generated from the same registry used by the CLI and engine.

## Failure cases

- Unknown paths return structured JSON with HTTP 404.
- POST requests return structured JSON with HTTP 405 and execute nothing.
- Empty hosts and invalid ports fail before binding.
- Bind failures return controlled CLI exit code 2.

## Known limitations

- Read-only endpoints only.
- No council analysis endpoint yet.
- No ledger, session, replay, simulation, scene, or event routes yet.
- No authentication or TLS; the bridge binds to localhost by default.
- No browser assets or GUI are included.
