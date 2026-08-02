from aviary.contracts import Bird,BirdMetadata,BirdOpinion
class BrotherApe(Bird):
 def metadata(self): return BirdMetadata("brother_ape","Brother Ape","1.0.0","Governor",1000)
 def voice(self): return "Can we build it, who benefits, and where is the receipt?"
 def schema(self): return {"type":"object"}
 def analyze(self,topic): return BirdOpinion("brother_ape","Build only what can be run, tested, explained, and removed without collapsing the system.",( "The CLI is the first client and SQLite is truth.",),("Ship one runnable vertical slice with verification.","Reject GUI work until CLI receipts exist."),("Atmosphere can conceal missing functionality.",),.95)
