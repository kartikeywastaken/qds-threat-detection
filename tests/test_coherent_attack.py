from attack_simulation.coherent_attack import CoherentAttackStrategy
from qds_protocol.key_distribution import distribute

def test_coherent():
    d=distribute(256,7)
    clean=CoherentAttackStrategy(0).transmit(d,0,9)
    attacked=CoherentAttackStrategy(1).transmit(d,0,9)
    print('Coherent QBER:',sum(r.error for r in attacked)/len(attacked))
    assert sum(r.error for r in clean)==0 and sum(r.error for r in attacked)>10
