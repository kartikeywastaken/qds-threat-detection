import numpy as np
from quantum_core.cv_channel_model import simulate_cv

def test_cv():
    a=simulate_cv(1,0); b=simulate_cv(.5,0)
    print('CV photons, before/after loss:',a['mean_photons'],b['mean_photons'])
    assert np.isclose(b['mean_photons'][1],.5*a['mean_photons'][1])
