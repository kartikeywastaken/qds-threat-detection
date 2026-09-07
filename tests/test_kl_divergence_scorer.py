import numpy as np
import pytest
from detection_engine.kl_divergence_scorer import kl_divergence

def test_kl():
    assert abs(kl_divergence(np.array([.5,.5]),np.array([.25,.75]))-.14384103622589045)<1e-12
    with pytest.raises(ValueError):kl_divergence(np.array([1,1]),np.array([.5,.5]))
