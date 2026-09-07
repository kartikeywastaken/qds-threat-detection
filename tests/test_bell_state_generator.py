import numpy as np
from quantum_core.bell_state_generator import bell_statevector, bell_density

def test_bell():
    state=bell_statevector().data
    clean=bell_density(0).data; noisy=bell_density(1).data
    print('Bell statevector:',state,'calibrated coherence:',noisy[0,3])
    assert np.allclose(state,[2**-.5,0,0,2**-.5])
    assert 0 < abs(noisy[0,3]) < abs(clean[0,3])
