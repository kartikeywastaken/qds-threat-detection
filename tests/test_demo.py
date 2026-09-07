from presentation.demo import demo

def test_end_to_end_demo(tmp_path):
    result=demo(tmp_path)
    assert result['http_status']==200 and result['decision']=='REJECT' and result['attribution']=='forgery'
