from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from aviary import __version__
from aviary.engine import AviaryEngine
from aviary.ledger import SQLiteLedger
from aviary.registry import BirdRegistry


COMMAND_ALIASES = {
    "birds": "birds",
    ":birds": "birds",
    "history": "history",
    ":history": "history",
    "help": "help",
    ":help": "help",
    "?": "help",
    "status": "status",
    ":status": "status",
    "schema": "schema",
    ":schema": "schema",
    "quit": "quit",
    ":quit": "quit",
    ":q": "quit",
    "exit": "quit",
}


def default_db_path() -> Path:
    return Path(os.environ.get("AVIARY_DB", Path.cwd() / "ledger" / "aviary.db"))


def build_engine(path: str | Path):
    registry = BirdRegistry()
    registry.discover()
    ledger = SQLiteLedger(path)
    for bird in registry.all():
        ledger.register_bird(bird.instance.metadata(), bird.module)
    return AviaryEngine(registry, ledger), ledger


def print_report(report) -> None:
    print("\n" + "═" * 58 + "\nTHE AVIARY — COUNCIL REPORT\n" + "═" * 58)
    for opinion in report.opinions:
        print(f"\n[{opinion.bird_id}] {opinion.summary}")
        for action in opinion.recommendations:
            print(f"  → {action}")
        for risk in opinion.risks:
            print(f"  ⚠ {risk}")
    print("\nBROTHER APE RULING\n" + report.decision.synthesis + "\n\nACTIONS")
    for action in report.decision.actions:
        print(f"  🍌 {action}")
    if report.decision.risks:
        print("\nRISKS")
        for risk in report.decision.risks:
            print(f"  ⚠ {risk}")
    print(
        f"\nReceipt: sha256:{report.receipt_hash}"
        f"\nSession: {report.session_id} | {report.elapsed_ms:.3f} ms"
        f" | confidence {report.decision.confidence:.3f}"
    )


def print_replay(replay: dict) -> None:
    print(
        "\n"
        + "═" * 58
        + f"\nTHE AVIARY — REPLAY SESSION #{replay['session_id']}\n"
        + "═" * 58
    )
    print(
        f"Topic: {replay['topic']['text']}"
        f"\nIntegrity: {'PASS' if replay['integrity']['valid'] else 'FAIL'}"
    )
    for opinion in replay["opinions"]:
        print(f"\n[{opinion['bird_id']}] {opinion['summary']}")
    print("\nBROTHER APE RULING\n" + replay["decision"]["synthesis"])
    print(
        f"\nReceipt: sha256:{replay['receipt_hash']}"
        f"\nStored runtime: {replay['elapsed_ms']:.3f} ms"
    )


def parse_repl_command(raw: str) -> tuple[str | None, list[str]]:
    parts = raw.split()
    if not parts:
        return None, []
    head = parts[0].lower()
    if head in {"replay", ":replay"}:
        return "replay", parts[1:]
    command = COMMAND_ALIASES.get(head)
    return command, parts[1:] if command else []


def print_help() -> None:
    print(
        "Commands:\n"
        "  birds | :birds              List loaded birds\n"
        "  history | :history          List recent sessions\n"
        "  replay <id> | :replay <id>  Verify and replay a session\n"
        "  status | :status            Show runtime status\n"
        "  schema | :schema            Show ledger schema version\n"
        "  help | :help | ?            Show this help\n"
        "  quit | :quit | exit         Close The Aviary\n"
        "Any other text is analyzed as a council topic."
    )


def execute_repl_command(engine: AviaryEngine, command: str, args: list[str]) -> bool:
    if command == "quit":
        return False
    if command == "help":
        print_help()
        return True
    if command == "birds":
        print("\n".join(engine.registry.ids()))
        return True
    if command == "history":
        rows = engine.ledger.recent_sessions()
        if not rows:
            print("No sessions recorded.")
        for row in rows:
            print(
                f"#{row['id']} {row['status']} {row['text']} "
                f"{row.get('sha256') or ''}".rstrip()
            )
        return True
    if command == "replay":
        if len(args) != 1 or not args[0].isdigit():
            print("Usage: replay <session-id>")
            return True
        try:
            print_replay(engine.ledger.replay_session(int(args[0])))
        except (LookupError, ValueError) as exc:
            print(f"ERROR: {exc}")
        return True
    if command == "status":
        print(f"Version: {__version__}")
        print(f"Database: {engine.ledger.path}")
        print(f"Schema: {engine.ledger.get_schema_version()}")
        print(f"Birds: {len(engine.registry.ids())}")
        print(f"Sessions: {len(engine.ledger.recent_sessions(limit=1000000))}")
        return True
    if command == "schema":
        print(f"Ledger schema version: {engine.ledger.get_schema_version()}")
        return True
    return True


def repl(engine: AviaryEngine) -> int:
    print(
        f"THE AVIARY {__version__}\n"
        "Type a topic. Type help for commands."
    )
    while True:
        try:
            raw = input("\naviary> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            continue
        command, args = parse_repl_command(raw)
        if command:
            if not execute_repl_command(engine, command, args):
                return 0
            continue
        try:
            print_report(engine.run(raw))
        except Exception as exc:
            print(f"ERROR: {exc}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="aviary")
    parser.add_argument("topic", nargs="*")
    parser.add_argument("--db", type=Path, default=default_db_path())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list-birds", action="store_true")
    parser.add_argument("--replay", type=int)
    args = parser.parse_args(argv)
    engine, ledger = build_engine(args.db)
    try:
        if args.list_birds:
            for bird in engine.registry.all():
                print(f"{bird.bird_id}\t{bird.instance.metadata().name}\t{bird.module}")
            return 0
        if args.replay is not None:
            replay = ledger.replay_session(args.replay)
            if args.json:
                print(json.dumps(replay, indent=2))
            else:
                print_replay(replay)
            return 0
        if args.topic:
            report = engine.run(" ".join(args.topic))
            if args.json:
                print(json.dumps(report.as_dict(), indent=2))
            else:
                print_report(report)
            return 0
        return repl(engine)
    finally:
        ledger.close()
