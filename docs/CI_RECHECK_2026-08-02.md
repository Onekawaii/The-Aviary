# CI Recheck Receipt

This commit intentionally retriggers the canonical `verify` workflow after the portable SQLite migration rollback fix.

Required result:

- Python 3.10: `python verify.py` passes.
- Python 3.13: `python verify.py` passes.
- The failed migration test confirms both schema DDL and its migration receipt are absent after rollback.
