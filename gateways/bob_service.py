"""Bob's separate HTTP process: verify with Bob's simulated E91 key only."""
import hashlib
import hmac
import logging
import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field
from .envelope import Envelope, canonical

app = FastAPI(title='Bob gateway — simulated E91')
ENGINE_URL = os.getenv('QDS_ENGINE_URL', 'http://127.0.0.1:8000')
logger = logging.getLogger('uvicorn.error')


class Verification(BaseModel):
    model_config = ConfigDict(extra='forbid')
    envelope: Envelope
    mac: str = Field(pattern=r'^[0-9a-f]{64}$')
    session_id: str = Field(min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9-]+$')


@app.post('/gate/verify')
async def verify(body: Verification):
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.get(f'{ENGINE_URL}/channel/{body.session_id}/key/bob')
            response.raise_for_status()
            key = bytes.fromhex(response.json()['key'])
        expected = hmac.new(key, canonical(body.envelope), hashlib.sha256).hexdigest()
        accepted = hmac.compare_digest(expected, body.mac)
        reason = ('Bob verified the envelope MAC using his independently derived simulated key.' if accepted else
                  'MAC mismatch: the gateways derived different keys after channel disturbance despite a '
                  'sampled error rate below the abort threshold, or the envelope was altered. Payment refused.')
    except (httpx.HTTPError, ValueError, KeyError):
        accepted, reason = False, 'Bob could not retrieve a valid session key. Payment refused.'
    logger.info('session=%s verdict=%s', body.session_id, 'accepted' if accepted else 'refused')
    return {'accept': accepted, 'stage': 'signature', 'reason': reason, 'simulated': True}
