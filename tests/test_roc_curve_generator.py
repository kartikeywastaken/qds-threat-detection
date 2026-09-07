from evaluation.roc_curve_generator import roc

def test_known_rankings():
    assert roc([0,0,1,1],[0,1,2,3])['auc']==1
    assert roc([0,0,1,1],[1,1,1,1])['auc']==.5
