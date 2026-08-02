# Plugin Quarantine

The Aviary records every discovered bird in the SQLite `plugins` table. The persisted `enabled` flag is now enforced when the engine starts.

## Commands

```text
plugins list
plugins disable raven
plugins enable raven
```

Changes are durable and written to the ledger history as `plugin.disabled` or `plugin.enabled` events. Enable/disable changes take effect on the next Aviary launch so the active registry remains stable during a council session.

## Demonstration

1. Start Aviary and run `plugins disable raven`.
2. Exit and restart with the same database.
3. Run `birds`; `raven` is absent.
4. Run `plugins list`; Raven remains registered but is marked `disabled`.
5. Re-enable Raven and restart to restore it.

## Failure cases

- Unknown plugin IDs are rejected and no row is created.
- Disabled plugins are not passed to the engine and cannot execute in the subprocess runtime.
- Discovery still validates plugin identity, voice, and schema before registration.

## Known limitations

- State changes require restart; hot-loading is deliberately excluded from this slice.
- Built-in birds currently begin enabled for backward compatibility. Third-party package discovery and default-disabled trust onboarding remain future work.
- Quarantine prevents execution but is not an operating-system security sandbox.
