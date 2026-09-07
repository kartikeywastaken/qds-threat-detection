from qds_protocol.key_distribution import distribute
from qds_protocol.signing_engine import sign
from qds_protocol.verification_engine import VerificationEngine

def test_verification():
    d=distribute(16,1); p,r=sign(d,'message'); v=VerificationEngine();v.register(d,r)
    e,_=v.verify(p); assert e.authenticated and e.fresh
    assert not v.verify(p)[0].fresh
    assert not v.verify(p.model_copy(update={'message':'tampered'}))[0].authenticated
