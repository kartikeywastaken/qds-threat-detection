from attack_simulation.attack_orchestrator import run_scenario

def test_intercept_resend():
    r=run_scenario('individual',1,0,31,8192).records
    q=sum(x.error for x in r)/len(r)
    print('100% intercept-resend QBER:',q)
    assert .23 < q < .27
