from attack_simulation.attack_orchestrator import run_scenario
from quantum_core.bell_state_generator import sample_chsh
from detection_engine.integrity_monitor import inspect
from attribution_engine.rule_engine import attribute

def test_rules():
    rows=sample_chsh(2048,.1,8)
    for name in ('forgery','impersonation','replay','channel_manipulation'):
        s=run_scenario(name,1,.1,7,512)
        result=attribute(inspect(s.records,rows,s.integrity,.045,.2))
        print(name,'=>',result['attack_class'],result['matched_flags'])
        assert result['attack_class']==name
