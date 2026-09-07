from evaluation.baseline_threshold_detector import design,detect

def test_fixed():
    d=design(.05,.2)
    print('Independent fixed-sample design:',d)
    assert d['fpr_under_h0']<=.01 and d['fnr_under_h1']<=.01
    assert detect([1]*d['n'],d['n'],d['cutoff'])['decision']=='REJECT'
