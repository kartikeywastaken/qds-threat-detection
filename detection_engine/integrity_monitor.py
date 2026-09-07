"""Observable-only statistical and classical-integrity fusion."""
import numpy as np
from qds_protocol.measurement_record import MeasurementRecord
from qds_protocol.verification_engine import IntegrityEvidence
from detection_engine.distribution_estimator import estimate
from detection_engine.kl_divergence_scorer import kl_divergence
from detection_engine.sprt_controller import SPRTController
from detection_engine.chsh_correlator import correlate
from detection_engine.min_entropy_evaluator import evaluate


def inspect(records: list[MeasurementRecord], rows: list[tuple[int,int,int,int]], integrity: IntegrityEvidence,
            p0: float, p1: float, alpha: float=.01, beta: float=.01) -> dict:
    """Apply explicit OR rule; thresholds and all component results remain visible."""
    distribution=estimate(records);chsh=correlate(rows); sprt=SPRTController(p0,p1,alpha,beta)
    for record in records: sprt.update(record.error)
    flags={'repeated_nonce':not integrity.fresh,'unknown_sender':not integrity.recognized_sender,
           'invalid_authentication':not integrity.authenticated,'quantum_mismatch':sprt.decision=='REJECT',
           'bell_deficit':chsh['upper']<2.4}
    decision='REJECT' if any(flags.values()) else sprt.decision
    qber=sum(r.error for r in records)/len(records)
    # Transparent dimensionless ranking for ROC, separate from stopping decision.
    score=max((qber-p0)/(p1-p0),(2.4-chsh['s'])/1.4,
              float(flags['repeated_nonce'] or flags['unknown_sender'] or flags['invalid_authentication']))
    return {'decision':decision,'sprt_decision':sprt.decision,'qber':qber,'kl_nats':kl_divergence(distribution,np.array([1-p0,p0])),
            'sprt':{'llr':sprt.llr,'trace':sprt.trace,'rounds':len(sprt.trace),'upper':sprt.upper,'lower':sprt.lower,'p0':p0,'p1':p1},
            'chsh':chsh,'entropy':evaluate(chsh,len(records)),'flags':flags,'score':score,'n':len(records)}
