from evaluation.run_full_evaluation import calibrate

def test_real_calibration():
    c=calibrate(.1,313)
    print('Measured honest calibration:',c)
    assert 0<c['observed_qber']<c['p0']<c['p1']<1
