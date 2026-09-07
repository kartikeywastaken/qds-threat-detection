from attack_simulation.attack_orchestrator import run_scenario,STRATEGIES
from quantum_core.bell_state_generator import sample_chsh
from detection_engine.integrity_monitor import inspect
from attribution_engine.rule_engine import attribute

def test_reports_repeat_across_hierarchy():
    pairs=sample_chsh(1024,.5,7362)
    assert pairs==sample_chsh(1024,.5,7362)
    for kind in STRATEGIES:
        first=run_scenario(kind,.6,.5,8197,64)
        second=run_scenario(kind,.6,.5,8197,64)
        assert first.records==second.records and first.payload==second.payload
        a=inspect(first.records,pairs,first.integrity,.08,.23)
        b=inspect(second.records,pairs,second.integrity,.08,.23)
        assert a==b and attribute(a)==attribute(b)
    print('Identical measured reports across',len(STRATEGIES),'scenario names with fixed seeds')

def test_zero_strength_is_honest_channel():
    reference=run_scenario('honest',0,.5,7162,64)
    for kind in STRATEGIES:
        current=run_scenario(kind,0,.5,7162,64)
        assert current.records==reference.records and current.integrity==reference.integrity
