import json,tempfile,time,unittest
from pathlib import Path
from aviary.cli import build_engine
from aviary.contracts import Topic
from aviary.registry import BirdRegistry

class AviaryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.engine,self.ledger=build_engine(Path(self.tmp.name)/"a.db")
 def tearDown(self): self.ledger.close(); self.tmp.cleanup()
 def test_discovers_six_birds(self): self.assertEqual(self.engine.registry.ids(),("duck","goose","raven","gobble","pheasant","brother_ape"))
 def test_contracts_valid(self):
  for b in self.engine.registry.all(): self.assertEqual(b.instance.schema()["type"],"object"); self.assertTrue(b.instance.voice())
 def test_all_birds_match_identity(self):
  for b in self.engine.registry.all(): self.assertEqual(b.instance.analyze(Topic("test")).bird_id,b.bird_id)
 def test_performance_budget(self):
  started=time.perf_counter()
  for b in self.engine.registry.all(): b.instance.analyze(Topic("speed"))
  self.assertLess(time.perf_counter()-started,.25)
 def test_empty_topic_fails(self):
  with self.assertRaises(ValueError): self.engine.run("  ")
 def test_run_records_receipt(self):
  r=self.engine.run("Build roots"); self.assertEqual(len(r.receipt_hash),64); self.assertEqual(len(r.opinions),6)
 def test_deterministic_decision(self): self.assertEqual(self.engine.run("same").decision,self.engine.run("same").decision)
 def test_replay_reconstructs(self):
  r=self.engine.run("Replay me"); x=self.ledger.replay_session(r.session_id); self.assertTrue(x["integrity"]["valid"]); self.assertEqual(x["receipt_hash"],r.receipt_hash)
 def test_replay_detects_tampering(self):
  r=self.engine.run("Tamper")
  with self.ledger.connection: self.ledger.connection.execute("UPDATE receipts SET content_json=? WHERE session_id=?",(json.dumps({"tampered":True}),r.session_id))
  self.assertFalse(self.ledger.replay_session(r.session_id)["integrity"]["valid"])
 def test_missing_replay_fails(self):
  with self.assertRaises(LookupError): self.ledger.replay_session(999)

if __name__=="__main__": unittest.main()
