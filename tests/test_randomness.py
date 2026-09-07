import pytest
from quantum_core.randomness import simulator_seed

def test_stream_separation():
    assert simulator_seed(7)==simulator_seed(7)
    assert len({simulator_seed(seed) for seed in range(100)})==100
    with pytest.raises(ValueError):simulator_seed(-1)
