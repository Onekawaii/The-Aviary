from __future__ import annotations

from typing import Sequence

from aviary.contracts import BirdOpinion, CouncilDecision, CouncilStrategy, Topic

class DefaultCouncil(CouncilStrategy):
    def aggregate(self, topic: Topic, opinions: Sequence[BirdOpinion]) -> CouncilDecision:
        ordered = tuple(sorted(opinions, key=lambda o: o.bird_id))
        actions = tuple(dict.fromkeys(a for o in ordered for a in o.recommendations))
        risks = tuple(dict.fromkeys(r for o in ordered for r in o.risks))
        synthesis = " ".join(f"{o.bird_id}: {o.summary}" for o in ordered)
        confidence = round(sum(o.confidence for o in ordered) / len(ordered), 3) if ordered else 0.0
        return CouncilDecision("Council Decision", synthesis, actions, risks, confidence)

class BrotherApeGovernor:
    def review(self, topic: Topic, decision: CouncilDecision, opinions: Sequence[BirdOpinion]) -> CouncilDecision:
        ape = next((o for o in opinions if o.bird_id == "brother_ape"), None)
        prefix = f"Brother Ape ruling: {ape.summary} " if ape else "Brother Ape ruling: "
        return CouncilDecision(
            "Brother Ape Ruling",
            prefix + decision.synthesis + " Preserve interfaces, demand executable receipts, and reject decorative complexity.",
            decision.actions,
            decision.risks,
            decision.confidence,
        )
