"""Alice's separate HTTP process: fetch Alice's key, MAC, ask Bob over HTTP."""
import hashlib
import hmac
import logging
import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from .envelope import Envelope, canonical

app = FastAPI(title='Alice gateway — simulated E91')
ENGINE_URL = os.getenv('QDS_ENGINE_URL', 'http://127.0.0.1:8000')
BOB_URL = os.getenv('BOB_GATEWAY_URL', 'http://127.0.0.1:8002')
logger = logging.getLogger('uvicorn.error')


class Authorisation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    envelope: Envelope


@app.post('/gate/authorise')
async def authorise(body: Authorisation):
    result = {'status': 'refused', 'stage': 'quantum_channel', 'session_id': None,
              'evidence': {'simulated': True}, 'simulated': True,
              'reason': 'Quantum channel service unavailable. Payment refused.'}
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.post(f'{ENGINE_URL}/channel/session', json={})
            response.raise_for_status()
            sid = response.json()['session_id']
            result['session_id'] = sid
            response = await client.get(f'{ENGINE_URL}/channel/{sid}/status')
            response.raise_for_status()
            evidence = response.json()
            # Allowlist evidence; neither key nor raw outcomes can enter responses/logs.
            result['evidence'] = {k: evidence[k] for k in ('qber', 'chsh_s', 'qber_threshold',
                'chsh_classical_bound', 'aborted', 'keys_match', 'raw_key_bits', 'final_key_bits', 'simulated')}
            if evidence['aborted']:
                result['reason'] = evidence['reason']
            else:
                response = await client.get(f'{ENGINE_URL}/channel/{sid}/key/alice')
                response.raise_for_status()
                key = bytes.fromhex(response.json()['key'])
                mac = hmac.new(key, canonical(body.envelope), hashlib.sha256).hexdigest()
                result['stage'] = 'signature'
                result['reason'] = 'Bob gateway unavailable. Payment refused.'
                response = await client.post(f'{BOB_URL}/gate/verify', json={
                    'envelope': body.envelope.model_dump(), 'mac': mac, 'session_id': sid})
                response.raise_for_status()
                verdict = response.json()
                result.update(status='accepted' if verdict['accept'] is True else 'refused',
                              mac=mac, reason=verdict['reason'])
        except (httpx.HTTPError, ValueError, KeyError):
            # Transport and invalid upstream data fail closed; no exception bodies logged.
            result['status'] = 'refused'
        logger.info('session=%s verdict=%s', result['session_id'], result['status'])
        try:
            await client.post(f'{ENGINE_URL}/channel/payment', json={
                'envelope': body.envelope.model_dump(), 'session_id': result['session_id'],
                'status': result['status'], 'stage': result['stage'], 'reason': result['reason']})
        except httpx.HTTPError:
            pass  # Display telemetry is never authorization.
    return result
