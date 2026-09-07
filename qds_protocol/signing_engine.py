"""Message binding plus transmission of one-time quantum signature tokens."""
import hashlib
import hmac
import json
from qds_protocol.measurement_record import Distribution, SignaturePayload, MeasurementRecord
from qds_protocol.teleportation_engine import transmit


def canonical(session_id: str, sender: str, nonce: str, message: str) -> bytes:
    """Unambiguous domain-separated envelope encoding."""
    return json.dumps(['QDS-DEMO-v1',session_id,sender,nonce,message],ensure_ascii=False,separators=(',',':')).encode()


def sign(distribution: Distribution, message: str, exposure: float=0., seed: int=1, sender: str='alice') -> tuple[SignaturePayload,list[MeasurementRecord]]:
    """Authenticate the envelope and teleport the session's BB84 states."""
    nonce=hashlib.sha256(distribution.auth_key+b'nonce').hexdigest()[:32]
    tag=hmac.new(distribution.auth_key,canonical(distribution.session_id,sender,nonce,message),hashlib.sha256).hexdigest()
    return SignaturePayload(session_id=distribution.session_id,sender=sender,nonce=nonce,message=message,tag=tag),transmit(distribution,exposure,seed)
