# The Aviary v0.1.0-alpha

A local-first, standard-library Python council engine. Birds are dynamically discovered plugins implementing one contract. Birds never call birds; the council invokes them independently. SQLite is the single source of truth.

## Termux

```bash
pkg install python git -y
git clone https://github.com/Onekawaii/The-Aviary.git
cd The-Aviary
python verify.py
python -m aviary
```

Interactive commands: `:birds`, `:history`, `:replay <session-id>`, `:quit`.

## One-shot use

```bash
python -m aviary "Should we build a local AI system?"
python -m aviary --replay 1
python -m aviary --replay 1 --json
```

## Architecture

- `aviary/contracts.py`: stable bird and council data contracts.
- `aviary/registry.py`: dynamic plugin discovery and validation.
- `aviary/engine.py`: headless execution pipeline.
- `aviary/council.py`: replaceable aggregation and Brother Ape governance.
- `aviary/ledger.py`: SQLite persistence, artifacts, history, and SHA-256 receipts.
- `aviary/cli.py`: terminal client only; it performs no reasoning.
- `aviary/birds/`: optional dynamically discovered bird plugins.

## Phase 1.5 — Receipt Replay

Replay reconstructs the stored topic, ordered bird opinions, final ruling, actions, risks, runtime, and receipt without rerunning birds. It recomputes SHA-256 for every opinion artifact and the final report before display. Tampering produces an integrity failure instead of being silently accepted.

Replay proves that stored content still matches its stored hashes. It does not prove that current bird code would generate the same result today.

## Receipt

A feature is complete only with source, tests, a verification command, documentation, a demonstration, a failure case, and known limitations.

Run:

```bash
python verify.py
```

Current verification: 10 automated tests plus CLI smoke and replay smoke.

## Known limitations

1. Birds run in-process. This is architectural isolation, not an OS security sandbox.
2. Analysis is deterministic scaffolding, not an LLM provider integration.
3. Schema validation is structural rather than full JSON Schema validation.
4. SQLite migrations are not versioned yet.
5. Replay is read-only and does not rerun historical plugin code.

**Sanctuary law:** if `python verify.py` fails, the sanctuary is closed.
