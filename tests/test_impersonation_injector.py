from attack_simulation.attack_orchestrator import run_scenario

def test_impersonation():
    assert not run_scenario('impersonation',1,0,n=32).integrity.recognized_sender
