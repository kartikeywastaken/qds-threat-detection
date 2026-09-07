from presentation.dashboard import draw

def test_empty_dashboard(tmp_path):
    target=tmp_path/'dashboard.png';draw(tmp_path/'events.jsonl',target)
    assert target.stat().st_size>1000
