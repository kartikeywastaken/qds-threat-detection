from quantum_core.ghz_state_generator import ghz_statevector

def test_ghz():
    p=ghz_statevector().probabilities()
    assert abs(p[0]-.5)<1e-12 and abs(p[-1]-.5)<1e-12
