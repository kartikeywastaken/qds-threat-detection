"""Actual localhost HTTP demo plus disk artifacts from the full quantum pipeline."""
from pathlib import Path
import json
import socket
import threading
import time
import httpx
import uvicorn
from qds_protocol.key_distribution import distribute
from qds_protocol.signing_engine import sign
from qds_protocol.verification_engine import VerificationEngine
from quantum_core.bell_state_generator import sample_chsh
from quantum_core.cv_channel_model import simulate_cv
from quantum_core.ghz_state_generator import ghz_statevector
from attack_simulation.individual_attack import IndividualAttackStrategy
from presentation.security_event_log import SecurityEventLog
from presentation.verification_api import create_app
from presentation.dashboard import draw


def demo(output: Path) -> dict:
    """Distribute → sign → intercept → verify over HTTP → detect → attribute → log."""
    output.mkdir(parents=True,exist_ok=True)
    d=distribute(512,821);payload,_=sign(d,'Approve teleportation channel',.1,822)
    records=IndividualAttackStrategy(1).transmit(d,.1,823)
    pairs=sample_chsh(8192,.1,824)
    verifier=VerificationEngine();verifier.register(d,records);log=SecurityEventLog(output/'events.jsonl')
    app=create_app(verifier,{d.session_id:pairs},log,.03,.18)
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128);port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'));thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.02)
        if not server.started:raise RuntimeError('HTTP demo server did not become ready')
        response=httpx.post(f'http://127.0.0.1:{port}/verify',json=payload.model_dump(),timeout=30);response.raise_for_status()
        report=response.json()
        replay=httpx.post(f'http://127.0.0.1:{port}/verify',json=payload.model_dump(),timeout=30);replay.raise_for_status()
    finally:
        server.should_exit=True;thread.join(5);sock.close()
    (output/'signature_payload.json').write_text(payload.model_dump_json(indent=2))
    (output/'measurement_records.json').write_text(json.dumps([r.model_dump() for r in records],indent=2))
    (output/'chsh_measurements.json').write_text(json.dumps(pairs))
    (output/'threat_report.json').write_text(json.dumps(report,indent=2))
    (output/'cv_channel.json').write_text(json.dumps(simulate_cv(),indent=2))
    (output/'ghz_probabilities.json').write_text(json.dumps(ghz_statevector().probabilities().tolist()))
    draw(output/'events.jsonl',output/'dashboard.png')
    result={'http_status':response.status_code,'decision':report['decision'],'qber':report['qber'],'attribution':report['attribution']['attack_class'],
            'log_events':len(log.read()),'replay_attribution':replay.json()['attribution']['attack_class'],'log':'events.jsonl','payload':'signature_payload.json'}
    (output/'http_demo.json').write_text(json.dumps(result,indent=2));print('HTTP demo:',result,flush=True);return result
