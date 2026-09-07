"""Receiver-side message integrity and independently held quantum evidence."""
from dataclasses import dataclass
import hmac
import hashlib
from qds_protocol.measurement_record import Distribution, SignaturePayload, MeasurementRecord
from qds_protocol.signing_engine import canonical


@dataclass(frozen=True)
class IntegrityEvidence:
    """Observable authentication/freshness facts, not attacker annotations."""
    authenticated: bool
    fresh: bool
    recognized_sender: bool


class VerificationEngine:
    """Single-process one-time session verifier; callers serialize verify operations."""
    def __init__(self) -> None:
        self.sessions: dict[str,tuple[Distribution,list[MeasurementRecord]]]={}
        self.used: set[tuple[str,str]]=set()

    def register(self, distribution: Distribution, records: list[MeasurementRecord]) -> None:
        """Store only receiver-generated records; client payloads cannot supply them."""
        if distribution.session_id in self.sessions: raise ValueError('Session already registered')
        if len(records)!=len(distribution.bits) or [r.index for r in records]!=list(range(len(records))):
            raise ValueError('Incomplete or out-of-order receipt')
        if any(r.expected!=b or r.basis!=a for r,b,a in zip(records,distribution.bits,distribution.bases)):
            raise ValueError('Receipt does not match private preparation')
        self.sessions[distribution.session_id]=(distribution,records)

    def verify(self, payload: SignaturePayload) -> tuple[IntegrityEvidence,list[MeasurementRecord]]:
        """Check MAC and consume authenticated nonce exactly once."""
        if payload.session_id not in self.sessions: raise KeyError('Unknown signature session')
        distribution,records=self.sessions[payload.session_id]
        expected=hmac.new(distribution.auth_key,canonical(payload.session_id,payload.sender,payload.nonce,payload.message),hashlib.sha256).hexdigest()
        authenticated=hmac.compare_digest(expected,payload.tag)
        key=(payload.session_id,payload.nonce)
        evidence=IntegrityEvidence(authenticated,key not in self.used,payload.sender=='alice')
        if authenticated: self.used.add(key)
        return evidence,records
