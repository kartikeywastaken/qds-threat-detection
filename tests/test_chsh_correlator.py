from quantum_core.bell_state_generator import sample_chsh
from detection_engine.chsh_correlator import correlate

def test_chsh():
    values=[correlate(sample_chsh(8192,.1,7,d))['s'] for d in (0,.5,1)]
    print('CHSH S at dephasing 0,.5,1:',values)
    assert 2.65<values[0]<2.9 and values[0]>values[1]>values[2] and 1.2<values[2]<1.6
