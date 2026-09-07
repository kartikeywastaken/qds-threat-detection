from attack_simulation.attack_orchestrator import run_scenario

def test_reproducible():
    a=run_scenario('individual',.7,.25,7,64)
    b=run_scenario('individual',.7,.25,7,64)
    assert a.records==b.records and a.integrity==b.integrity
