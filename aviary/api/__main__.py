from __future__ import annotations

import argparse

from aviary.api.server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the local Aviary JSON bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", default="ledger/aviary.db")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        server = create_server(args.host, args.port, ledger_path=args.db)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    host, port = server.server_address[:2]
    print(f"AVIARY_BRIDGE_READY http://{host}:{port}", flush=True)
    print(
        "Endpoints: GET /api/health, GET /api/birds, GET /api/simulations",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAviary bridge stopped safely.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
