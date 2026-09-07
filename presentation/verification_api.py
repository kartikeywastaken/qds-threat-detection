"""FastAPI verification endpoint with server-owned physical measurement evidence."""
from threading import Lock
from typing import Literal, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qds_protocol.measurement_record import SignaturePayload
from qds_protocol.verification_engine import VerificationEngine
from detection_engine.integrity_monitor import inspect
from attribution_engine.rule_engine import attribute
from presentation.security_event_log import SecurityEventLog


class QuantumExecutionInfo(BaseModel):
    """Metadata about the quantum backend used for this execution."""
    backend: str
    processor: str | None = None
    simulated: bool = True
    noisy: bool = False
    display_name: str | None = None


class ThreatReport(BaseModel):
    """JSON response exposing actual computed components and deterministic attribution."""
    session_id: str
    decision: Literal['ACCEPT', 'REJECT', 'INCONCLUSIVE']
    qber: float
    statistics: dict
    attribution: dict
    quantum_execution: QuantumExecutionInfo | None = None


class QuantumStatusResponse(BaseModel):
    """Response for the quantum backend status endpoint."""
    backend: str
    available: bool
    processor: str | None = None
    simulated: bool = True
    noisy: bool = False
    display_name: str | None = None
    details: dict[str, Any] = {}


def create_app(
    verifier: VerificationEngine,
    chsh_receipts: dict[str, list[tuple[int, int, int, int]]],
    log: SecurityEventLog,
    p0: float = .06,
    p1: float = .21,
    *,
    quantum_backend_name: str = 'ideal',
) -> FastAPI:
    """Create a local verification service; measurement records are never client input.

    Args:
        verifier: The pre-loaded receiver verification engine.
        chsh_receipts: Per-session CHSH measurement rows.
        log: Security event log for audit trail.
        p0: Null hypothesis QBER (honest threshold).
        p1: Alternative hypothesis QBER (attack threshold).
        quantum_backend_name: Name of the configured quantum backend ('ideal' or 'qvm').
    """
    app = FastAPI(title='Teleportation QDS threat monitor', version='0.1.0')
    lock = Lock()

    # Resolve backend metadata once at startup (lazy — avoids expensive QVM init at import)
    _backend_meta: dict[str, Any] = {}

    def _get_backend_meta() -> dict[str, Any]:
        nonlocal _backend_meta
        if _backend_meta:
            return _backend_meta
        try:
            from quantum_core.factory import get_quantum_backend
            backend = get_quantum_backend(quantum_backend_name)
            _backend_meta = backend.metadata
        except Exception as exc:
            _backend_meta = {
                'backend': quantum_backend_name,
                'available': False,
                'error': f'{type(exc).__name__}: {exc}',
                'simulated': True,
                'noisy': False,
                'processor': None,
                'display_name': 'Unavailable',
            }
        return _backend_meta

    @app.post('/verify', response_model=ThreatReport)
    def verify(payload: SignaturePayload) -> ThreatReport:
        """Atomically verify freshness, evaluate signals and append a security event."""
        with lock:
            if payload.session_id not in verifier.sessions or payload.session_id not in chsh_receipts:
                raise HTTPException(404, 'Unknown or incomplete signature session')
            integrity, records = verifier.verify(payload)
            statistics = inspect(records, chsh_receipts[payload.session_id], integrity, p0, p1)

            meta = _get_backend_meta()
            qe_info = QuantumExecutionInfo(
                backend=meta.get('backend', quantum_backend_name),
                processor=meta.get('processor'),
                simulated=meta.get('simulated', True),
                noisy=meta.get('noisy', False),
                display_name=meta.get('display_name'),
            )

            report = ThreatReport(
                session_id=payload.session_id,
                decision=statistics['decision'],
                qber=statistics['qber'],
                statistics=statistics,
                attribution=attribute(statistics),
                quantum_execution=qe_info,
            )
            log.append(report.model_dump())
            return report

    @app.get('/events')
    def events() -> list[dict]:
        """Expose local telemetry for the live dashboard."""
        return log.read()

    @app.get('/health')
    def health() -> dict:
        """Readiness reflects the loaded receiver session count."""
        return {'status': 'ready', 'sessions': len(verifier.sessions)}

    @app.get('/quantum/status', response_model=QuantumStatusResponse)
    def quantum_status() -> QuantumStatusResponse:
        """Report the active quantum backend identity and availability.

        The 'simulated' field is always true — QVM does not execute on
        physical hardware.  It is a noisy virtual Willow processor model
        running entirely locally.
        """
        meta = _get_backend_meta()
        return QuantumStatusResponse(
            backend=meta.get('backend', quantum_backend_name),
            available='error' not in meta,
            processor=meta.get('processor'),
            simulated=meta.get('simulated', True),
            noisy=meta.get('noisy', False),
            display_name=meta.get('display_name'),
            details={
                k: v for k, v in meta.items()
                if k not in ('backend', 'processor', 'simulated', 'noisy', 'display_name')
                and isinstance(v, (str, int, float, bool, type(None)))
            },
        )

    return app
