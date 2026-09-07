import pytest
from presentation.security_event_log import SecurityEventLog

def test_log(tmp_path):
    log=SecurityEventLog(tmp_path/'events.jsonl');log.append({'x':1});log.append({'x':2})
    assert len(log.read())==2
    log.path.write_text(log.path.read_text().replace('"x": 1','"x": 9'))
    with pytest.raises(ValueError):log.read()
