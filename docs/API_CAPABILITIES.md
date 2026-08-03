# Aviary Bridge Capabilities

## Purpose

`GET /api/capabilities` provides a machine-readable inventory of the Local Bridge contracts that are actually implemented. Local clients can feature-detect routes instead of assuming that a later bridge phase exists.

The manifest is declarative only. It does not execute council reasoning, mutate the ledger, or advertise unfinished routes.

## Run

```bash
python -m aviary.api --db ledger/aviary.db
```

## Demonstration

```text
GET http://127.0.0.1:8787/api/capabilities
```

The response contains:

- `service`
- `api_version`
- `read_only`
- `count`
- `capabilities`, each with `method`, `path`, and `purpose`

All advertised methods are currently `GET`.

## Failure case

Query parameters are rejected because the manifest has no filtering contract:

```text
GET /api/capabilities?extra=1
→ HTTP 400
→ {"error":"invalid_request", ...}
```

Unknown routes and non-GET requests continue to use the bridge's existing structured 404 and 405 responses.

## Verification

```bash
python verify.py
python -m unittest tests.test_api_capabilities tests.test_api_capabilities_route -v
```

## Known limitations

- The manifest describes routes, not runtime authorization or transport security.
- It is not an OpenAPI document.
- It does not prove that a particular persisted receipt is valid; use the simulation verification route for that.
- The bridge remains localhost-first, read-only, unauthenticated, and without TLS.
- No council, session, scene, event, browser asset, or GUI route is included.
