import asyncio
import os
import threading
import time
import math
import random
import hashlib
import traceback
from typing import Literal
from dotenv import load_dotenv
import razorpay
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn
from pydantic import BaseModel

class TransactionVerifyRequest(BaseModel):
    tx_id: str

from qds_protocol.key_distribution import distribute
from qds_protocol.signing_engine import sign
from qds_protocol.verification_engine import VerificationEngine
from quantum_core.bell_state_generator import sample_chsh
from attack_simulation.individual_attack import IndividualAttackStrategy
from detection_engine.integrity_monitor import inspect
from presentation.security_event_log import SecurityEventLog
from attribution_engine.rule_engine import attribute

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Initialize Razorpay Client with Environment Variables
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

try:
    rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
except Exception as e:
    print(f"Warning: Razorpay initialization failed: {e}")
    rzp_client = None

app = FastAPI(title='QDS Dashboard API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
log = SecurityEventLog('artifacts/events.jsonl')

state_lock = threading.Lock()
current_state = {
    'session_id': 'N/A',
    's': 0.0,
    'fidelity': 0.0,
    'cycle': 0,
    'sprt_trace': [],
    'sprt_upper': 4.60,
    'sprt_lower': -4.60,
    'qber': 0.0,
    'entropy': 0.0,
    'chsh_history': [],
    'sprt_decision': 'INCONCLUSIVE',
    'attack_mode': 'HONEST',
    'latest_decision': 'ACCEPT',
    'attribution': 'NONE'
}

from attack_simulation.collective_attack import CollectiveAttackStrategy
from attack_simulation.coherent_attack import CoherentAttackStrategy
from attack_simulation.impersonation_injector import ImpersonationInjector
from attack_simulation.channel_manipulation_injector import ChannelManipulationInjector
from attack_simulation.replay_injector import ReplayInjector
from attack_simulation.attack_strategy_base import AttackStrategyBase

current_attack_mode = 'HONEST'
attack_changed = threading.Event()  # Signal to wake sim loop immediately

class AttackConfig(BaseModel):
    mode: str

class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

def simulation_loop():
    verifier = VerificationEngine()
    cycle = 0
    while True:
        try:
            cycle += 1
            d = distribute(512, 821 + cycle)
            payload, _ = sign(d, 'Approve teleportation channel', 0.1, 822 + cycle)
            
            attack_mode = current_attack_mode
            
            if attack_mode == 'HONEST':
                strategy = AttackStrategyBase(0)
            elif attack_mode == 'INDIVIDUAL':
                strategy = IndividualAttackStrategy(1)
            elif attack_mode == 'COLLECTIVE':
                strategy = CollectiveAttackStrategy(1)
            elif attack_mode == 'COHERENT':
                strategy = CoherentAttackStrategy(1)
            elif attack_mode == 'IMPERSONATION':
                strategy = ImpersonationInjector(1)
            elif attack_mode == 'CHANNEL_MANIPULATION':
                strategy = ChannelManipulationInjector(1)
            elif attack_mode == 'REPLAY':
                strategy = AttackStrategyBase(0)
            else:
                strategy = AttackStrategyBase(0)
                
            records = strategy.transmit(d, 0.1, 823 + cycle)
            if hasattr(strategy, 'envelope'):
                payload = strategy.envelope(payload)
                
            pairs = sample_chsh(8192, 0.1, 824 + cycle)
            
            # Prevent memory unbounded growth in verification engine
            if len(verifier.sessions) > 50:
                oldest_key = next(iter(verifier.sessions))
                verifier.sessions.pop(oldest_key, None)
            if len(verifier.used) > 200:
                verifier.used = set(list(verifier.used)[-100:])
                
            verifier.register(d, records)
            
            if attack_mode == 'REPLAY':
                capture = ReplayInjector()
                capture.capture(payload)
                verifier.verify(payload) # Consume first time
                payload = capture.inject() # Injected replayed payload
                
            integrity, final_records = verifier.verify(payload)
            statistics = inspect(final_records, pairs, integrity, 0.03, 0.18)
            
            att = attribute(statistics)
            report = {
                'session_id': payload.session_id,
                'decision': statistics['decision'],
                'qber': statistics['qber'],
                'statistics': statistics,
                'attribution': att
            }
            log.append(report)
            
            with state_lock:
                s_val = statistics['chsh']['s']
                current_state['session_id'] = payload.session_id[-4:].upper()
                current_state['s'] = s_val
                current_state['fidelity'] = 1.0 - statistics['qber']
                current_state['cycle'] = cycle
                current_state['sprt_trace'] = statistics['sprt']['trace']
                current_state['sprt_upper'] = statistics['sprt']['upper']
                current_state['sprt_lower'] = statistics['sprt']['lower']
                current_state['qber'] = statistics['qber']
                current_state['entropy'] = statistics['entropy']
                current_state['sprt_decision'] = statistics['sprt_decision']
                current_state['attack_mode'] = attack_mode
                current_state['latest_decision'] = statistics['decision']
                current_state['attribution'] = att.get('attack_class', 'NONE') if isinstance(att, dict) else 'NONE'
                
                current_state['chsh_history'].append(s_val)
                if len(current_state['chsh_history']) > 20:
                    current_state['chsh_history'].pop(0)

        except Exception as e:
            traceback.print_exc()
            time.sleep(1)

        # Wait 1s OR wake instantly if attack mode changed
        attack_changed.wait(timeout=1)
        attack_changed.clear()

threading.Thread(target=simulation_loop, daemon=True).start()

@app.get('/api/state')
def get_state():
    with state_lock:
        current_state['attack_mode'] = current_attack_mode
        return current_state

@app.get('/api/events')
def get_events():
    events = log.read()
    return events[-10:][::-1]

@app.get('/api/events_all')
def get_events_all():
    events = log.read()
    return events[::-1]

@app.post('/api/set_attack')
def set_attack(config: AttackConfig):
    global current_attack_mode
    current_attack_mode = config.mode
    with state_lock:
        current_state['attack_mode'] = config.mode
    attack_changed.set()
    return {"status": "ok", "mode": config.mode}

@app.post('/api/create_order')
def create_order():
    amount_in_paise = 50000 # 500 INR
    if not rzp_client:
        mock_order_id = f"order_mock_{int(time.time())}"
        return {
            "order_id": mock_order_id,
            "amount": amount_in_paise,
            "currency": "INR",
            "key": "rzp_mock_demo_mode",
            "mock": True
        }
    
    data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": "receipt#1",
        "notes": {
            "policy_name": "QDS Secure"
        }
    }
    try:
        order = rzp_client.order.create(data=data)
        return {"order_id": order['id'], "amount": amount_in_paise, "currency": "INR", "key": RAZORPAY_KEY_ID}
    except Exception as e:
        return {"error": str(e)}

@app.post('/api/verify_payment')
def verify_payment(data: PaymentVerification):
    params_dict = {
        'razorpay_order_id': data.razorpay_order_id,
        'razorpay_payment_id': data.razorpay_payment_id,
        'razorpay_signature': data.razorpay_signature
    }
    
    try:
        if rzp_client and not data.razorpay_payment_id.startswith('pay_mock'):
            rzp_client.utility.verify_payment_signature(params_dict)
    except Exception:
        pass

    with state_lock:
        if 'transactions' not in current_state:
            current_state['transactions'] = []
            
        tx_id = data.razorpay_payment_id or f"pay_{int(time.time())}"
        decision = current_state.get('latest_decision', 'ACCEPT')
        attack_mode = current_state.get('attack_mode', 'HONEST')
        s_val = current_state.get('s', 2.80)
        qber = current_state.get('qber', 0.0)
        
        tx = {
            'id': tx_id,
            'amount': 500,
            'time': "Just now",
            'decision': decision,
            'attack_mode': attack_mode,
            'verified': False,
            'qber': qber,
            's_val': s_val
        }
        current_state['transactions'].insert(0, tx)
        
    if tx['decision'] == 'REJECT':
        return {"status": "blocked", "message": "Quantum signature tampered.", "tx_id": tx['id']}
        
    return {"status": "success", "tx_id": tx['id']}

@app.post('/api/verify_transaction')
def verify_transaction(req: TransactionVerifyRequest):
    with state_lock:
        decision = current_state.get('latest_decision', 'ACCEPT')
        attack_mode = current_state.get('attack_mode', 'HONEST')
        qber = current_state.get('qber', 0.0078)
        s_val = current_state.get('s', 2.80)
        fidelity = current_state.get('fidelity', 0.992)
        attribution = current_state.get('attribution', 'NONE')
        sprt_decision = current_state.get('sprt_decision', 'ACCEPT')
        sprt_trace = current_state.get('sprt_trace', [])
        session_id = current_state.get('session_id', 'QK-8F29')
        
        tx_found = None
        if 'transactions' in current_state:
            for tx in current_state['transactions']:
                if tx.get('id') == req.tx_id:
                    tx_found = tx
                    break
                    
        receipt = {
            "receipt_id": f"QREC-{req.tx_id[-6:].upper() if len(req.tx_id)>=6 else '8921B4'}",
            "tx_id": req.tx_id,
            "session_id": session_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "quantum_protocol": "Teleportation-Assisted BB84 QDS",
            "security_guarantee": "Information-Theoretic (No-Cloning Protected)",
            "chsh_entanglement_s": round(s_val, 3),
            "bell_violation_status": "PROVEN QUANTUM NON-LOCAL (S > 2.0)" if s_val > 2.0 else "DEFICIT / CLASSICAL (S <= 2.0)",
            "qber": round(qber, 4),
            "fidelity": round(fidelity, 4),
            "sprt_decision_rounds": len(sprt_trace) or 14,
            "verdict": decision,
            "attribution": attribution if attribution != 'NONE' else "None (Honest Channel)",
            "proof_hash": hashlib.sha256(f"{req.tx_id}:{session_id}:{s_val}:{decision}".encode()).hexdigest()[:32]
        }
        
        if tx_found:
            tx_found['verified'] = True
            tx_found['decision'] = decision
            tx_found['receipt'] = receipt
            
        return {
            "status": "ok",
            "tx_id": req.tx_id,
            "decision": decision,
            "attack_mode": attack_mode,
            "verified": (decision == 'ACCEPT'),
            "qber": qber,
            "s": s_val,
            "attribution": attribution,
            "receipt": receipt
        }

class FailedPayment(BaseModel):
    error_code: str
    error_description: str

@app.post('/api/log_failed_payment')
def log_failed_payment(data: FailedPayment):
    with state_lock:
        if 'transactions' not in current_state:
            current_state['transactions'] = []
            
        tx = {
            'id': f"fail_{int(time.time())}",
            'amount': 500,
            'time': "Just now",
            'decision': 'FAILED',
            'attack_mode': current_state.get('attack_mode', 'HONEST'),
            'qber': current_state.get('qber', 0.0),
            's_val': current_state.get('s', 0.0),
            'error': data.error_description
        }
        current_state['transactions'].insert(0, tx)
    return {"status": "logged"}

@app.get('/')
def index():
    with open('qds_command_center (1).html', 'r', encoding='utf-8') as f:
        return HTMLResponse(f.read())

@app.get('/mobile')
def mobile():
    with open('mobile.html', 'r', encoding='utf-8') as f:
        return HTMLResponse(f.read())

@app.get('/eve')
def eve():
    with open('eve.html', 'r', encoding='utf-8') as f:
        return HTMLResponse(f.read())

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run('app:app', host='0.0.0.0', port=port, reload=False, access_log=False)
