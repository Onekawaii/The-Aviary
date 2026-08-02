from __future__ import annotations
import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(cmd):
 print("+"," ".join(map(str,cmd)))
 p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
 if p.stdout: print(p.stdout,end="")
 if p.stderr: print(p.stderr,end="",file=sys.stderr)
 if p.returncode: raise SystemExit(p.returncode)

def main():
 run([sys.executable,"-m","unittest","discover","-s","tests","-v"])
 with tempfile.TemporaryDirectory() as tmp:
  db=Path(tmp)/"verify.db"
  p=subprocess.run([sys.executable,"-m","aviary","--db",str(db),"--json","Verify the sanctuary foundation"],cwd=ROOT,text=True,capture_output=True)
  if p.returncode: print(p.stdout); print(p.stderr,file=sys.stderr); return p.returncode
  report=json.loads(p.stdout); assert len(report["opinions"])==6 and len(report["receipt_hash"])==64
  q=subprocess.run([sys.executable,"-m","aviary","--db",str(db),"--replay",str(report["session_id"]),"--json"],cwd=ROOT,text=True,capture_output=True)
  if q.returncode: print(q.stdout); print(q.stderr,file=sys.stderr); return q.returncode
  replay=json.loads(q.stdout); assert replay["integrity"]["valid"] and replay["receipt_hash"]==report["receipt_hash"]
  print(f"SMOKE PASS session={report['session_id']} receipt={report['receipt_hash']}")
 print("AVIARY VERIFY PASS 🍌"); return 0
if __name__=="__main__": raise SystemExit(main())
