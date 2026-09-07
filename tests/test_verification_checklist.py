from evaluation.verification_checklist import entropy_experiment

def test_restricted_probe_experiment():
    r=entropy_experiment(.04,0,31,1024)
    print('Restricted probe success / bound:',r['empirical_success'],r['bound'])
    assert r['below_bound'] and r['successes']>0
