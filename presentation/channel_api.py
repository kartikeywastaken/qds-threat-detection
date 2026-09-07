"""Local simulated E91 API, independent from teleportation attack controls."""
from collections import OrderedDict
from threading import RLock
from typing import Literal
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from e91 import run_e91
from e91.session_store import SessionStore

router = APIRouter(prefix='/channel', tags=['E91 — simulated'])
store = SessionStore()
control_lock = RLock()
eve_fraction = 0.
payments = OrderedDict()


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rounds: int = Field(default=1024, ge=1, le=8192, strict=True)
    eve_fraction: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    seed: int = Field(default=7, ge=0, lt=2**31, strict=True)


class AttackRequest(BaseModel):
    fraction: float = Field(ge=0, le=1, allow_inf_nan=False)


class PublicEnvelope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    transfer_id: str = Field(max_length=64)
    from_user: str = Field(max_length=100)
    to_user: str = Field(max_length=100)
    amount_paise: int = Field(gt=0, strict=True)
    nonce: str = Field(max_length=128)


class PaymentEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    envelope: PublicEnvelope
    session_id: str | None = Field(default=None, max_length=64)
    status: Literal['accepted', 'refused']
    stage: Literal['quantum_channel', 'signature', 'committed']
    reason: str = Field(max_length=600)


def session_or_404(session_id):
    try:
        return store.get(session_id)
    except KeyError:
        raise HTTPException(404, 'Session missing or expired') from None


@router.post('/session')
def create_session(body: SessionRequest):
    with control_lock:
        fraction = eve_fraction if body.eve_fraction is None else body.eve_fraction
    result = run_e91(body.rounds, eve=fraction, seed=body.seed)
    return {'session_id': store.add(result), 'simulated': True}


@router.post('/attack')
def set_attack(body: AttackRequest):
    global eve_fraction
    with control_lock:
        eve_fraction = body.fraction
    return {'fraction': body.fraction, 'simulated': True}


@router.get('/latest')
def latest():
    with control_lock:
        payment = next(reversed(payments.values()), None)
        fraction = eve_fraction
    return {'session_id': store.latest(), 'fraction': fraction, 'payment': payment, 'simulated': True}


@router.post('/payment')
def payment_event(body: PaymentEvent):
    # An educational localhost event feed, not an authorization source.
    with control_lock:
        ident = body.envelope.transfer_id
        payments[ident] = {**body.model_dump(), 'simulated': True}
        payments.move_to_end(ident)
        while len(payments) > 64:
            payments.popitem(last=False)
    return {'recorded': True}


@router.get('/{session_id}/status')
def status(session_id: str):
    return session_or_404(session_id).to_dict()


@router.get('/{session_id}/key/{party}')
def key(session_id: str, party: Literal['alice', 'bob'], response: Response):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return {'key': store.key(session_id, party)}
    except KeyError:
        raise HTTPException(404, 'Key unavailable: session aborted, missing or expired') from None


@router.get('/{session_id}/rounds')
def rounds(session_id: str, limit: int = Query(default=64, ge=1, le=128)):
    result = session_or_404(session_id)
    # Only already published, sacrificed sample bits. Never disclose surviving
    # secret bits, even across repeated/paginated animation requests.
    public = [{'round': i, 'alice': a, 'bob': b, 'agree': a == b}
              for i, a, b, published in result._rounds if published][:limit]
    return {'rounds': public, 'scope': 'published sample; discarded from key', 'simulated': True}
