import socket
import threading
import time
import httpx
import uvicorn
from qds_protocol.key_distribution import distribute
from qds_protocol.signing_engine import sign
from qds_protocol.verification_engine import VerificationEngine
from quantum_core.bell_state_generator import sample_chsh
from presentation.security_event_log import SecurityEventLog
from presentation.verification_api import create_app


def _start_server(app):
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sock.listen(128)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started: break
        time.sleep(.02)
    return server, thread, sock, port


def test_http(tmp_path):
    d=distribute(512,7);p,r=sign(d,'real HTTP signature',.1,8)
    v=VerificationEngine();v.register(d,r);log=SecurityEventLog(tmp_path/'events.jsonl')
    app=create_app(v,{d.session_id:sample_chsh(2048,.1,9)},log,.045,.2)
    server, thread, sock, port = _start_server(app)
    try:
        assert server.started
        response=httpx.post(f'http://127.0.0.1:{port}/verify',json=p.model_dump())
        print('Real HTTP status/report:',response.status_code,response.json()['decision'],response.json()['qber'])
        assert response.status_code==200 and response.json()['decision']=='ACCEPT'
        assert httpx.post(f'http://127.0.0.1:{port}/verify',json=p.model_dump()).json()['attribution']['attack_class']=='replay'
        assert len(log.read())==2
    finally:
        server.should_exit=True;thread.join(5);sock.close()


def test_verify_response_includes_quantum_execution(tmp_path):
    """The /verify response must include quantum_execution metadata."""
    d = distribute(64, 11); p, r = sign(d, 'qe metadata test', 0., 12)
    v = VerificationEngine(); v.register(d, r)
    log = SecurityEventLog(tmp_path / 'events.jsonl')
    app = create_app(v, {d.session_id: sample_chsh(512, .0, 13)}, log, .045, .2,
                     quantum_backend_name='ideal')
    server, thread, sock, port = _start_server(app)
    try:
        assert server.started
        resp = httpx.post(f'http://127.0.0.1:{port}/verify', json=p.model_dump())
        assert resp.status_code == 200
        body = resp.json()
        assert 'quantum_execution' in body, 'Response must include quantum_execution field'
        qe = body['quantum_execution']
        assert 'backend' in qe
        assert 'simulated' in qe
        assert qe['simulated'] is True, 'QVM must always be reported as simulated'
    finally:
        server.should_exit = True; thread.join(5); sock.close()


def test_quantum_status_endpoint(tmp_path):
    """GET /quantum/status must return backend availability and simulated=true."""
    d = distribute(64, 21); p, r = sign(d, 'status test', 0., 22)
    v = VerificationEngine(); v.register(d, r)
    log = SecurityEventLog(tmp_path / 'events.jsonl')
    app = create_app(v, {d.session_id: sample_chsh(512, .0, 23)}, log,
                     quantum_backend_name='ideal')
    server, thread, sock, port = _start_server(app)
    try:
        assert server.started
        resp = httpx.get(f'http://127.0.0.1:{port}/quantum/status')
        assert resp.status_code == 200
        body = resp.json()
        assert 'backend' in body
        assert 'available' in body
        assert 'simulated' in body
        assert body['simulated'] is True, 'Backend must always report simulated=true'
        assert body['backend'] == 'ideal'
        print('Quantum status:', body)
    finally:
        server.should_exit = True; thread.join(5); sock.close()
