from detection_engine.min_entropy_evaluator import evaluate

def test_entropy():
    result=evaluate({'lower':2.5},32)
    assert result['chsh_bits_per_round_lower']>0 and 0<result['restricted_iid_forgery_bound']<1
