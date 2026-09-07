from qds_protocol.teleportation_engine import fidelity

def test_teleportation():
    values=[fidelity(exposure=x) for x in (0,.5,1)]
    print('Teleportation fidelity at exposure 0,.5,1:',values)
    assert values[0]>=.99 and values[0]>values[1]>values[2]
