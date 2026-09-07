"""Local QDS command center. Every quantum observation is simulated with Qiskit Aer."""
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
import logging
import os
import threading
import time
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
from attack_simulation.attack_orchestrator import run_scenario
from quantum_core.bell_state_generator import sample_chsh
from detection_engine.integrity_monitor import inspect
from attribution_engine.rule_engine import attribute
from presentation.live_log import BoundedEventLog

ROOT = Path(__file__).resolve().parent
state_lock = threading.Lock()
attack_changed = threading.Event()
stop_simulation = threading.Event()
current_attack_mode = 'HONEST'
current_state = {
    'session_id': 'N/A', 's': 0., 'fidelity': 0., 'cycle': 0, 'sprt_trace': [],
    'sprt_upper': 4.60, 'sprt_lower': -9.21, 'qber': 0., 'entropy': 0.,
    'chsh_history': [], 'sprt_decision': 'INCONCLUSIVE', 'attack_mode': 'HONEST',
    'latest_decision': 'INCONCLUSIVE', 'attribution': 'none', 'simulated': True,
    'quantum_backend': 'Qiskit Aer', 'bell_outcome': None, 'error': None,
}
log = BoundedEventLog(Path(os.getenv('QDS_EVENT_PATH', str(ROOT / 'artifacts/events.jsonl'))))


class AttackConfig(BaseModel):
    """Select only implemented teleportation scenarios, independent of E91."""
    mode: Literal['HONEST', 'INDIVIDUAL', 'COLLECTIVE', 'COHERENT', 'IMPERSONATION', 'CHANNEL_MANIPULATION', 'REPLAY']


def simulation_loop() -> None:
    """Publish measured observations; each cycle owns a verifier, bounding session memory."""
    cycle = 0
    while not stop_simulation.is_set():
        started = time.monotonic()
        with state_lock:
            mode = current_attack_mode
            attack_changed.clear()
        cycle += 1
        try:
            scenario = run_scenario(mode.lower(), 0. if mode == 'HONEST' else 1., .1, 821 + cycle, 512)
            pairs = sample_chsh(4096, .1, 20000 + cycle, 1. if mode == 'IMPERSONATION' else 0.)
            statistics = inspect(scenario.records, pairs, scenario.integrity, .03, .18, beta=.0001)
            attribution = attribute(statistics)
            report = {'session_id': scenario.payload.session_id, 'decision': statistics['decision'],
                      'qber': statistics['qber'], 'statistics': statistics, 'attribution': attribution,
                      'simulated': True, 'quantum_backend': 'Qiskit Aer', 'attack_mode': mode}
            log.append(report)
            with state_lock:
                if current_attack_mode == mode:
                    history = (current_state['chsh_history'] + [statistics['chsh']['s']])[-20:]
                    current_state.update(session_id=scenario.payload.session_id[-4:].upper(),
                        s=statistics['chsh']['s'], fidelity=1-statistics['qber'], cycle=cycle,
                        sprt_trace=statistics['sprt']['trace'], sprt_upper=statistics['sprt']['upper'],
                        sprt_lower=statistics['sprt']['lower'], qber=statistics['qber'],
                        entropy=statistics['entropy'], sprt_decision=statistics['sprt_decision'],
                        attack_mode=mode, latest_decision=statistics['decision'],
                        attribution=attribution['attack_class'], chsh_history=history,
                        bell_outcome=''.join(map(str, scenario.records[0].bell_bits)), error=None)
        except Exception:
            # Acquisition failures are visible and cannot leave a stale acceptance displayed.
            logging.exception('Teleportation simulation failed')
            with state_lock:
                current_state.update(latest_decision='INCONCLUSIVE', error='Simulation unavailable; no verdict issued.')
        attack_changed.wait(timeout=max(0., 1 - (time.monotonic()-started)))


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Start exactly one simulation worker, after startup rather than during import."""
    stop_simulation.clear()
    worker = threading.Thread(target=simulation_loop, name='teleportation-simulation', daemon=True)
    worker.start()
    yield
    stop_simulation.set(); attack_changed.set(); worker.join(timeout=10)


app = FastAPI(title='QDS Dashboard API — simulated', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


def teleportation_verdict() -> dict:
    """Current QDS teleportation-channel verdict. Available to a separate payment gate."""
    with state_lock:
        return {'decision': current_state['latest_decision'], 'qber': current_state['qber'],
                'chsh_s': current_state['s'], 'attribution': current_state['attribution']}


@app.get('/api/state')
def get_state() -> dict:
    with state_lock:
        return deepcopy(current_state)


@app.get('/api/events')
def get_events() -> list[dict]:
    return log.read()[-10:][::-1]


@app.get('/api/events_all')
def get_events_all() -> list[dict]:
    return log.read()[::-1]


@app.post('/api/set_attack')
def set_attack(config: AttackConfig) -> dict:
    global current_attack_mode
    with state_lock:
        current_attack_mode = config.mode
        current_state.update(attack_mode=config.mode, latest_decision='INCONCLUSIVE')
        attack_changed.set()
    return {'status': 'success', 'mode': config.mode, 'simulated': True}


@app.get('/', response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    uvicorn.run(app, host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '8000')))
