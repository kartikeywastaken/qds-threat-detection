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

def test_http(tmp_path):
    d=distribute(512,7);p,r=sign(d,'real HTTP signature',.1,8)
    v=VerificationEngine();v.register(d,r);log=SecurityEventLog(tmp_path/'events.jsonl')
    app=create_app(v,{d.session_id:sample_chsh(2048,.1,9)},log,.045,.2)
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128);port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.02)
        assert server.started
        response=httpx.post(f'http://127.0.0.1:{port}/verify',json=p.model_dump())
        print('Real HTTP status/report:',response.status_code,response.json()['decision'],response.json()['qber'])
        assert response.status_code==200 and response.json()['decision']=='ACCEPT'
        assert httpx.post(f'http://127.0.0.1:{port}/verify',json=p.model_dump()).json()['attribution']['attack_class']=='replay'
        assert len(log.read())==2
    finally:
        server.should_exit=True;thread.join(5);sock.close()
