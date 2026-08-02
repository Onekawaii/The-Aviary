from __future__ import annotations

import argparse,json,os
from pathlib import Path
from aviary import __version__
from aviary.engine import AviaryEngine
from aviary.ledger import SQLiteLedger
from aviary.registry import BirdRegistry

def default_db_path(): return Path(os.environ.get("AVIARY_DB",Path.cwd()/"ledger"/"aviary.db"))
def build_engine(path):
 r=BirdRegistry(); r.discover(); l=SQLiteLedger(path)
 for b in r.all(): l.register_bird(b.instance.metadata(),b.module)
 return AviaryEngine(r,l),l

def print_report(report):
 print("\n"+"═"*58+"\nTHE AVIARY — COUNCIL REPORT\n"+"═"*58)
 for o in report.opinions:
  print(f"\n[{o.bird_id}] {o.summary}")
  for a in o.recommendations: print(f"  → {a}")
  for r in o.risks: print(f"  ⚠ {r}")
 print("\nBROTHER APE RULING\n"+report.decision.synthesis+"\n\nACTIONS")
 for a in report.decision.actions: print(f"  🍌 {a}")
 if report.decision.risks:
  print("\nRISKS")
  for r in report.decision.risks: print(f"  ⚠ {r}")
 print(f"\nReceipt: sha256:{report.receipt_hash}\nSession: {report.session_id} | {report.elapsed_ms:.3f} ms | confidence {report.decision.confidence:.3f}")

def print_replay(x):
 print("\n"+"═"*58+f"\nTHE AVIARY — REPLAY SESSION #{x['session_id']}\n"+"═"*58)
 print(f"Topic: {x['topic']['text']}\nIntegrity: {'PASS' if x['integrity']['valid'] else 'FAIL'}")
 for o in x['opinions']:
  print(f"\n[{o['bird_id']}] {o['summary']}")
 print("\nBROTHER APE RULING\n"+x['decision']['synthesis'])
 print(f"\nReceipt: sha256:{x['receipt_hash']}\nStored runtime: {x['elapsed_ms']:.3f} ms")

def repl(engine):
 print(f"THE AVIARY {__version__}\nType a topic. Commands: :birds, :history, :replay <id>, :quit")
 while True:
  try: raw=input("\naviary> ").strip()
  except (EOFError,KeyboardInterrupt): print(); return 0
  if not raw: continue
  if raw in {":quit",":q","quit","exit"}: return 0
  if raw==":birds": print("\n".join(engine.registry.ids())); continue
  if raw==":history":
   for row in engine.ledger.recent_sessions(): print(f"#{row['id']} {row['status']} {row['text']} {row.get('sha256') or ''}")
   continue
  if raw.startswith(":replay"):
   parts=raw.split()
   if len(parts)!=2 or not parts[1].isdigit(): print("Usage: :replay <session-id>"); continue
   try: print_replay(engine.ledger.replay_session(int(parts[1])))
   except (LookupError,ValueError) as e: print(f"ERROR: {e}")
   continue
  try: print_report(engine.run(raw))
  except Exception as e: print(f"ERROR: {e}")

def main(argv=None):
 p=argparse.ArgumentParser(prog="aviary"); p.add_argument("topic",nargs="*"); p.add_argument("--db",type=Path,default=default_db_path()); p.add_argument("--json",action="store_true"); p.add_argument("--list-birds",action="store_true"); p.add_argument("--replay",type=int)
 a=p.parse_args(argv); engine,ledger=build_engine(a.db)
 try:
  if a.list_birds:
   for b in engine.registry.all(): print(f"{b.bird_id}\t{b.instance.metadata().name}\t{b.module}")
   return 0
  if a.replay is not None:
   x=ledger.replay_session(a.replay); print(json.dumps(x,indent=2) if a.json else "",end="") if a.json else print_replay(x); return 0
  if a.topic:
   x=engine.run(" ".join(a.topic)); print(json.dumps(x.as_dict(),indent=2) if a.json else "",end="") if a.json else print_report(x); return 0
  return repl(engine)
 finally: ledger.close()
