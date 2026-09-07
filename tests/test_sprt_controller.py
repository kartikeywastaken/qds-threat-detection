import math
from detection_engine.sprt_controller import SPRTController

def test_likelihood():
    s=SPRTController(.05,.25)
    for x in [0,1,0]:s.update(x)
    assert abs(s.llr-(math.log(5)+2*math.log(.75/.95)))<1e-12
    for _ in range(100):s.update(1)
    print('SPRT computed rejection:',s.llr,'after',len(s.trace),'rounds')
    assert s.decision=='REJECT'
    trace=s.trace.copy();s.update(0);assert s.trace==trace
