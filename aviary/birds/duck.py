from aviary.contracts import Bird,BirdMetadata,BirdOpinion
class Duck(Bird):
 def metadata(self): return BirdMetadata("duck","Duck","1.0.0","Genesis",20)
 def voice(self): return "What new idea is trying to be born?"
 def schema(self): return {"type":"object"}
 def analyze(self,topic): return BirdOpinion("duck",f"Make '{topic.text.rstrip('.?!')}' executable before expanding it.",( "Reduce it to input, transformation, and verifiable output.",),("Build the thinnest end-to-end path first.","Preserve one delightful element."),confidence=.78)
