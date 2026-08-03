from __future__ import annotations

import argparse
from collections.abc import Sequence

from aviary.simulation import cli as verify_cli
from aviary.simulation import run_cli


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation",
        description="Run or verify deterministic simulation receipts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run a JSON simulation spec and persist its receipt")
    run_parser.add_argument("args", nargs=argparse.REMAINDER)

    verify_parser = subparsers.add_parser("verify", help="load and verify a persisted simulation receipt")
    verify_parser.add_argument("args", nargs=argparse.REMAINDER)

    parsed = parser.parse_args(list(argv) if argv is not None else None)
    if parsed.command == "run":
        return run_cli.main(parsed.args)
    return verify_cli.main(parsed.args)


if __name__ == "__main__":
    raise SystemExit(main())
