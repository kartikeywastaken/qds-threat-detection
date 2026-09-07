from fastapi import FastAPI
from fastapi.testclient import TestClient
from e91 import run_e91
from e91.session_store import SessionStore
from presentation.channel_api import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_separate_keys_and_aborted_endpoints():
    for fraction in (0, 1):
        sid = client.post('/channel/session', json={'eve_fraction': fraction}).json()['session_id']
        status = client.get(f'/channel/{sid}/status').json()
        a = client.get(f'/channel/{sid}/key/alice')
        b = client.get(f'/channel/{sid}/key/bob')
        assert 'alice_key' not in status and 'bob_key' not in status
        if fraction:
            assert status['aborted'] and status['reason']
            assert a.status_code == b.status_code == 404
        else:
            assert a.json()['key'] == b.json()['key']
            assert a.json()['key'] not in str(status)
            assert a.headers['cache-control'] == 'no-store'


def test_bounded_sessions_and_ttl():
    now = [0.]
    store = SessionStore(max_sessions=8, ttl_seconds=10, clock=lambda: now[0])
    result = run_e91()
    first = store.add(result)
    for _ in range(200):
        store.add(result)
    assert len(store) == 8
    try:
        store.get(first)
        assert False, 'oldest session was not evicted'
    except KeyError:
        pass
    now[0] = 11
    assert len(store) == 0 and store.latest() is None


def test_attack_next_session_and_public_rounds():
    client.post('/channel/attack', json={'fraction': .1})
    sid = client.post('/channel/session', json={}).json()['session_id']
    status = client.get(f'/channel/{sid}/status').json()
    assert status['eve_fraction'] == .1 and not status['keys_match']
    rows = client.get(f'/channel/{sid}/rounds?limit=12').json()['rounds']
    assert len(rows) == 12 and all(r['agree'] == (r['alice'] == r['bob']) for r in rows)
    assert client.get(f'/channel/{sid}/rounds?limit=129').status_code == 422
    assert client.post('/channel/session', json={'rounds': 0}).status_code == 422
    client.post('/channel/attack', json={'fraction': 0})
