"""Real HTTP integration across three independent Python processes."""
import hashlib
import hmac
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import httpx
import pytest
from gateways.envelope import canonical


@pytest.fixture(scope='module')
def services(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('gateway-http')
    processes, logs, urls = [], {}, {}
    def start(name, module, extra):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        path = tmp / (name + '.log')
        log = path.open('w')
        env = {**os.environ, **extra}
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', module, '--host', '127.0.0.1',
            '--port', str(port)], cwd=Path(__file__).resolve().parents[1], env=env, stdout=log, stderr=log)
        processes.append((process, log)); logs[name] = path
        url = f'http://127.0.0.1:{port}'
        for _ in range(150):
            try:
                if httpx.get(url + '/openapi.json').status_code == 200:
                    urls[name] = url
                    return url
            except httpx.HTTPError:
                pass
            time.sleep(.1)
        raise RuntimeError(name + ' did not start')
    try:
        engine = start('engine', 'app:app', {'QDS_EVENT_PATH': str(tmp/'events.jsonl')})
        bob = start('bob', 'gateways.bob_service:app', {'QDS_ENGINE_URL': engine})
        start('alice', 'gateways.alice_service:app', {'QDS_ENGINE_URL': engine, 'BOB_GATEWAY_URL': bob})
        yield urls, logs
    finally:
        for process, log in reversed(processes):
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            log.close()


def test_http_honest_light_abort_tamper_and_logs(services):
    urls, logs = services
    envelope = {'transfer_id': 'demo-transfer', 'from_user': 'alice', 'to_user': 'bob',
                'amount_paise': 10000, 'nonce': 'a1'*16}
    keys = []
    with httpx.Client(timeout=30) as c:
        for fraction, expected in [(0, 'accepted'), (.1, 'refused'), (1, 'refused')]:
            c.post(urls['engine'] + '/channel/attack', json={'fraction': fraction}).raise_for_status()
            calls_before = logs['bob'].read_text().count('POST /gate/verify')
            response = c.post(urls['alice'] + '/gate/authorise', json={'envelope': envelope})
            response.raise_for_status(); result = response.json()
            assert result['status'] == expected
            sid = result['session_id']
            if fraction == 1:
                assert result['stage'] == 'quantum_channel' and 'mac' not in result
                assert logs['bob'].read_text().count('POST /gate/verify') == calls_before
                continue
            assert result['stage'] == 'signature' and len(result['mac']) == 64
            for party in ('alice', 'bob'):
                key = c.get(urls['engine'] + f'/channel/{sid}/key/{party}').json()['key']
                keys.append(key)
                assert key not in response.text
            if fraction == 0:
                assert hmac.compare_digest(result['mac'], hmac.new(bytes.fromhex(keys[-1]), canonical(envelope), hashlib.sha256).hexdigest())
                changed = {**envelope, 'amount_paise': 10001}
                verdict = c.post(urls['bob'] + '/gate/verify', json={
                    'session_id': sid, 'envelope': changed, 'mac': result['mac']}).json()
                assert verdict['accept'] is False and verdict['stage'] == 'signature'
        for log in logs.values():
            assert all(key not in log.read_text() for key in keys)


def test_canonical_domain_and_order():
    envelope = {'nonce': 'n'*16, 'amount_paise': 1, 'to_user': 'bob', 'from_user': 'alice', 'transfer_id': 'id'}
    assert canonical(envelope).startswith(b'{"_domain":"QDS-WALLET-v1","amount_paise":1,')
    assert canonical(envelope) == canonical(dict(reversed(list(envelope.items()))))
