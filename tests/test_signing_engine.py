from qds_protocol.key_distribution import distribute
from qds_protocol.signing_engine import sign

def test_signing():
    payload,records=sign(distribute(128,8),'hello',0,3)
    print('Noiseless signature mismatches:',sum(r.error for r in records),'/',len(records))
    assert sum(r.error for r in records)==0 and len(payload.tag)==64
