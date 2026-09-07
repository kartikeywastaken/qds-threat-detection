from attack_simulation.attack_orchestrator import run_scenario
from quantum_core.bell_state_generator import sample_chsh
from detection_engine.integrity_monitor import inspect

def test_monitor():
    rows=sample_chsh(2048,.1,9)
    clean=run_scenario('honest',0,.1,7,512);bad=run_scenario('individual',1,.1,8,512)
    a=inspect(clean.records,rows,clean.integrity,.045,.20);b=inspect(bad.records,rows,bad.integrity,.045,.20)
    print('Honest/attack:',a['decision'],a['qber'],b['decision'],b['qber'])
    assert a['decision']=='ACCEPT' and b['decision']=='REJECT'
