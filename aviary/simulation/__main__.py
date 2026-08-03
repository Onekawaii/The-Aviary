from __future__ import annotations

import argparse
from collections.abc import Sequence

from aviary.simulation import cli as verify_cli
from aviary.simulation import export_cli, list_cli, run_cli


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aviary.simulation",
        description="Run, list, export, or verify deterministic simulation receipts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "run",
        help="run a JSON simulation spec and persist its receipt",
        add_help=False,
    )
    subparsers.add_parser(
        "list",
        help="list persisted simulation receipts",
        add_help=False,
    )
    subparsers.add_parser(
        "export",
        help="export one persisted simulation receipt as JSON",
        add_help=False,
    )
    subparsers.add_parser(
        "verify",
        help="load and verify a persisted simulation receipt",
        add_help=False,
    )

    parsed, delegated_args = parser.parse_known_args(list(argv) if argv is not None else None)
    if parsed.command == "run":
        return run_cli.main(delegated_args)
    if parsed.command == "list":
        return list_cli.main(delegated_args)
    if parsed.command == "export":
        return export_cli.main(delegated_args)
    return verify_cli.main(delegated_args)


if __name__ == "__main__":
    raise SystemExit(main())
