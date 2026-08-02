from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Mapping

from aviary.contracts import BirdOpinion, CouncilDecision, CouncilStrategy, Topic
from aviary.council import BrotherApeGovernor, DefaultCouncil
from aviary.ledger import SQLiteLedger
from aviary.registry import BirdRegistry

@dataclass(frozen=True, slots=True)
class RunReport:
    session_id: int
    topic: Topic
    opinions: tuple[BirdOpinion,...]
    decision: CouncilDecision
    elapsed_ms: float
    receipt_hash: str
    def as_dict(self)->dict[str,Any]: return asdict(self)

class AviaryEngine:
    def __init__(self,registry:BirdRegistry,ledger:SQLiteLedger,council:CouncilStrategy|None=None,governor:BrotherApeGovernor|None=None):
        self.registry=registry; self.ledger=ledger; self.council=council or DefaultCouncil(); self.governor=governor or BrotherApeGovernor()
    def run(self,text:str,context:Mapping[str,Any]|None=None)->RunReport:
        text=text.strip()
        if not text: raise ValueError("topic text may not be empty")
        started=perf_counter(); topic=Topic(text,context or {}); sid=self.ledger.start_session(topic); opinions=[]
        for loaded in self.registry.all():
            opinion=loaded.instance.analyze(topic)
            if opinion.bird_id!=loaded.bird_id: raise ValueError(f"bird {loaded.bird_id} returned mismatched bird_id {opinion.bird_id}")
            opinions.append(opinion); self.ledger.record_opinion(sid,opinion)
        decision=self.governor.review(topic,self.council.aggregate(topic,opinions),opinions)
        elapsed=round((perf_counter()-started)*1000,3); receipt=self.ledger.finish_session(sid,decision,elapsed)
        return RunReport(sid,topic,tuple(opinions),decision,elapsed,receipt)
