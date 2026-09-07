"""FastAPI verification endpoint with server-owned physical measurement evidence."""
from threading import Lock
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qds_protocol.measurement_record import SignaturePayload
from qds_protocol.verification_engine import VerificationEngine
from detection_engine.integrity_monitor import inspect
from attribution_engine.rule_engine import attribute
from presentation.security_event_log import SecurityEventLog


class ThreatReport(BaseModel):
    """JSON response exposing actual computed components and deterministic attribution."""
    session_id: str
    decision: Literal['ACCEPT','REJECT','INCONCLUSIVE']
    qber: float
    statistics: dict
    attribution: dict


def create_app(verifier: VerificationEngine, chsh_receipts: dict[str,list[tuple[int,int,int,int]]],
               log: SecurityEventLog, p0: float=.06, p1: float=.21) -> FastAPI:
    """Create a local verification service; measurement records are never client input."""
    app=FastAPI(title='Teleportation QDS threat monitor',version='0.1.0'); lock=Lock()

    @app.post('/verify',response_model=ThreatReport)
    def verify(payload: SignaturePayload) -> ThreatReport:
        """Atomically verify freshness, evaluate signals and append a security event."""
        with lock:
            if payload.session_id not in verifier.sessions or payload.session_id not in chsh_receipts:
                raise HTTPException(404,'Unknown or incomplete signature session')
            integrity,records=verifier.verify(payload)
            statistics=inspect(records,chsh_receipts[payload.session_id],integrity,p0,p1)
            report=ThreatReport(session_id=payload.session_id,decision=statistics['decision'],qber=statistics['qber'],
                                statistics=statistics,attribution=attribute(statistics))
            log.append(report.model_dump())
            return report

    @app.get('/events')
    def events() -> list[dict]:
        """Expose local telemetry for the live dashboard."""
        return log.read()

    @app.get('/health')
    def health() -> dict:
        """Readiness reflects the loaded receiver session count."""
        return {'status':'ready','sessions':len(verifier.sessions)}
    return app
