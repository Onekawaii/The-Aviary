from aviary.contracts import Bird,BirdMetadata,BirdOpinion
class Goose(Bird):
 def metadata(self): return BirdMetadata("goose","Goose","1.0.0","Expansion",30)
 def voice(self): return "How does this grow?"
 def schema(self): return {"type":"object"}
 def analyze(self,topic): return BirdOpinion("goose","Growth should occur through replaceable interfaces rather than shared implementation knowledge.",( "Stable contracts let clients and plugins arrive without rewriting the kernel.",),("Version public contracts before graphical clients.",),("Unchecked plugin privileges can become an attack surface.",),.8)
