from attack_simulation.collective_attack import CollectiveAttackStrategy
from qds_protocol.key_distribution import distribute

def test_collective():
    strategy=CollectiveAttackStrategy(1)
    records=strategy.transmit(distribute(512,7),0,8)
    print('Collective QBER:',sum(r.error for r in records)/len(records),'joint probe samples:',len(strategy.probe_outcomes))
    assert sum(r.error for r in records)>30 and len(strategy.probe_outcomes)==256
