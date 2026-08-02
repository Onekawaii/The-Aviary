from __future__ import annotations

import hashlib, json, sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aviary.contracts import BirdMetadata, BirdOpinion, CouncilDecision, Topic

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY,text TEXT NOT NULL,context_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY,topic_id INTEGER NOT NULL REFERENCES topics(id),status TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,elapsed_ms REAL,final_json TEXT);
CREATE TABLE IF NOT EXISTS birds(bird_id TEXT PRIMARY KEY,name TEXT NOT NULL,version TEXT NOT NULL,role TEXT NOT NULL,metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS opinions(id INTEGER PRIMARY KEY,session_id INTEGER NOT NULL REFERENCES sessions(id),bird_id TEXT NOT NULL,opinion_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY,session_id INTEGER REFERENCES sessions(id),kind TEXT NOT NULL,content_json TEXT NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS artifacts(id INTEGER PRIMARY KEY,session_id INTEGER REFERENCES sessions(id),bird_id TEXT,artifact_type TEXT NOT NULL,content_json TEXT NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,event_type TEXT NOT NULL,entity_id TEXT,payload_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plugins(id INTEGER PRIMARY KEY,plugin_id TEXT NOT NULL UNIQUE,module TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,metadata_json TEXT NOT NULL,discovered_at TEXT NOT NULL);
"""

def utcnow() -> str: return datetime.now(timezone.utc).isoformat()
def canonical_json(value: Any) -> str: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha256_text(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()

class SQLiteLedger:
    def __init__(self,path: str|Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.connection=sqlite3.connect(self.path); self.connection.row_factory=sqlite3.Row
        self.connection.executescript(SCHEMA); self.connection.commit()
    def close(self): self.connection.close()
    def register_bird(self,metadata: BirdMetadata,module: str):
        payload=canonical_json(asdict(metadata)); now=utcnow()
        with self.connection:
            self.connection.execute("INSERT INTO birds VALUES(?,?,?,?,?) ON CONFLICT(bird_id) DO UPDATE SET name=excluded.name,version=excluded.version,role=excluded.role,metadata_json=excluded.metadata_json",(metadata.bird_id,metadata.name,metadata.version,metadata.role,payload))
            self.connection.execute("INSERT INTO plugins(plugin_id,module,metadata_json,discovered_at) VALUES(?,?,?,?) ON CONFLICT(plugin_id) DO UPDATE SET module=excluded.module,metadata_json=excluded.metadata_json,discovered_at=excluded.discovered_at",(metadata.bird_id,module,payload,now))
    def start_session(self,topic: Topic)->int:
        now=utcnow()
        with self.connection:
            cur=self.connection.execute("INSERT INTO topics(text,context_json,created_at) VALUES(?,?,?)",(topic.text,canonical_json(dict(topic.context)),now)); topic_id=int(cur.lastrowid)
            cur=self.connection.execute("INSERT INTO sessions(topic_id,status,started_at) VALUES(?,?,?)",(topic_id,"running",now)); sid=int(cur.lastrowid)
            self.connection.execute("INSERT INTO history(event_type,entity_id,payload_json,created_at) VALUES(?,?,?,?)",("session.started",str(sid),canonical_json({"topic_id":topic_id}),now))
        return sid
    def record_opinion(self,sid:int,opinion:BirdOpinion)->str:
        now=utcnow(); payload=canonical_json(asdict(opinion)); digest=sha256_text(payload)
        with self.connection:
            self.connection.execute("INSERT INTO opinions(session_id,bird_id,opinion_json,created_at) VALUES(?,?,?,?)",(sid,opinion.bird_id,payload,now))
            self.connection.execute("INSERT INTO artifacts(session_id,bird_id,artifact_type,content_json,sha256,created_at) VALUES(?,?,?,?,?,?)",(sid,opinion.bird_id,"bird_opinion",payload,digest,now))
        return digest
    def finish_session(self,sid:int,decision:CouncilDecision,elapsed_ms:float)->str:
        now=utcnow(); payload=canonical_json(asdict(decision)); digest=sha256_text(payload)
        with self.connection:
            self.connection.execute("UPDATE sessions SET status='complete',finished_at=?,elapsed_ms=?,final_json=? WHERE id=?",(now,elapsed_ms,payload,sid))
            self.connection.execute("INSERT INTO receipts(session_id,kind,content_json,sha256,created_at) VALUES(?,?,?,?,?)",(sid,"final_report",payload,digest,now))
            self.connection.execute("INSERT INTO history(event_type,entity_id,payload_json,created_at) VALUES(?,?,?,?)",("session.completed",str(sid),canonical_json({"sha256":digest}),now))
        return digest
    def recent_sessions(self,limit:int=10):
        rows=self.connection.execute("SELECT s.id,t.text,s.status,s.started_at,s.elapsed_ms,r.sha256 FROM sessions s JOIN topics t ON t.id=s.topic_id LEFT JOIN receipts r ON r.session_id=s.id AND r.kind='final_report' ORDER BY s.id DESC LIMIT ?",(limit,)).fetchall()
        return [dict(r) for r in rows]
    def replay_session(self,sid:int)->dict[str,Any]:
        row=self.connection.execute("SELECT s.*,t.text,t.context_json,r.sha256 receipt_sha256,r.content_json receipt_json FROM sessions s JOIN topics t ON t.id=s.topic_id LEFT JOIN receipts r ON r.session_id=s.id AND r.kind='final_report' WHERE s.id=?",(sid,)).fetchone()
        if row is None: raise LookupError(f"session {sid} does not exist")
        if row["status"]!="complete" or not row["final_json"] or not row["receipt_sha256"]: raise ValueError(f"session {sid} is not replayable because it is incomplete")
        opinion_rows=self.connection.execute("SELECT o.bird_id,o.opinion_json,a.sha256 artifact_sha256 FROM opinions o LEFT JOIN artifacts a ON a.session_id=o.session_id AND a.bird_id=o.bird_id AND a.artifact_type='bird_opinion' WHERE o.session_id=? ORDER BY o.id",(sid,)).fetchall()
        if not opinion_rows: raise ValueError(f"session {sid} has no recorded opinions")
        opinions=[]; checks=[]
        for item in opinion_rows:
            actual=sha256_text(item["opinion_json"]); valid=bool(item["artifact_sha256"]) and actual==item["artifact_sha256"]
            checks.append({"bird_id":item["bird_id"],"expected":item["artifact_sha256"],"actual":actual,"valid":valid}); opinions.append(json.loads(item["opinion_json"]))
        receipt_payload=row["receipt_json"] or row["final_json"]; receipt_actual=sha256_text(receipt_payload)
        receipt_valid=receipt_actual==row["receipt_sha256"] and receipt_payload==row["final_json"]
        return {"session_id":sid,"topic":{"text":row["text"],"context":json.loads(row["context_json"])},"status":row["status"],"elapsed_ms":row["elapsed_ms"],"opinions":opinions,"decision":json.loads(row["final_json"]),"receipt_hash":row["receipt_sha256"],"integrity":{"valid":receipt_valid and all(c["valid"] for c in checks),"receipt":{"expected":row["receipt_sha256"],"actual":receipt_actual,"valid":receipt_valid},"opinions":checks}}
