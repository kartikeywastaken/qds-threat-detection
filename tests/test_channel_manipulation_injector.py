from attack_simulation.attack_orchestrator import run_scenario

def test_tamper():
    e=run_scenario('channel_manipulation',1,0,n=32).integrity
    assert not e.authenticated and e.recognized_sender
