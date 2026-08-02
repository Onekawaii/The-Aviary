from aviary.contracts import Bird,BirdMetadata,BirdOpinion
class Pheasant(Bird):
 def metadata(self): return BirdMetadata("pheasant","Pheasant","1.0.0","Legacy",60)
 def voice(self): return "What survives?"
 def schema(self): return {"type":"object"}
 def analyze(self,topic): return BirdOpinion("pheasant","What survives is a small documented contract, reproducible receipts, and readable storage.",( "Longevity comes from clear boundaries and migrations.",),("Document extension points beside runnable examples.","Keep migrations explicit once schema changes."),confidence=.82)
