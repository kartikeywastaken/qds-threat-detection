import numpy as np
import pytest
from detection_engine.distribution_estimator import estimate
from qds_protocol.measurement_record import MeasurementRecord

def test_distribution():
    r=[MeasurementRecord(index=i,expected=0,observed=i%2,basis='Z',bell_bits=(0,0)) for i in range(4)]
    assert np.allclose(estimate(r),[.5,.5])
    with pytest.raises(ValueError): estimate([])
