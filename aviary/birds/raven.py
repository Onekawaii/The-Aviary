from aviary.contracts import Bird,BirdMetadata,BirdOpinion
class Raven(Bird):
 def metadata(self): return BirdMetadata("raven","Raven","1.0.0","Pattern",40)
 def voice(self): return "What is not obvious?"
 def schema(self): return {"type":"object"}
 def analyze(self,topic): return BirdOpinion("raven","The hidden dependency is the contract defining a valid result.",( "Schemas are executable boundaries, not decoration.",),("Make validation explicit and testable.",),("Dynamic discovery may load unwanted modules unless scope is explicit.",),.84)
