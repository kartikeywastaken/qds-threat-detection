import pytest
from attack_simulation.replay_injector import ReplayInjector
from attack_simulation.attack_orchestrator import run_scenario

def test_replay():
    with pytest.raises(ValueError): ReplayInjector().inject()
    e=run_scenario('replay',1,0,n=32).integrity
    assert e.authenticated and not e.fresh
