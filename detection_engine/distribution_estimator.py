"""Empirical mismatch distributions from validated receiver records."""
import numpy as np
from qds_protocol.measurement_record import MeasurementRecord


def estimate(records: list[MeasurementRecord], pseudocount: float=.5) -> np.ndarray:
    """Return Jeffreys-smoothed [match,mismatch] frequencies (§4)."""
    if not records or not np.isfinite(pseudocount) or pseudocount<0: raise ValueError('Invalid sample or pseudocount')
    if [r.index for r in records]!=list(range(len(records))): raise ValueError('Records must have contiguous chronological indices')
    errors=sum(r.error for r in records)
    return (np.array([len(records)-errors,errors])+pseudocount)/(len(records)+2*pseudocount)
