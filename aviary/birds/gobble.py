from aviary.contracts import Bird,BirdMetadata,BirdOpinion
class Gobble(Bird):
 def metadata(self): return BirdMetadata("gobble","Gobble","1.0.0","Chaos",50)
 def voice(self): return "What happens if everything goes wrong?"
 def schema(self): return {"type":"object"}
 def analyze(self,topic): return BirdOpinion("gobble","Assume a bird crashes, stalls, or corrupts its output.",( "A single unbounded plugin can block the council.",),("Record failures as receipts.","Add process isolation before untrusted plugins."),("Current isolation is contractual, not a security boundary.",),.9)
