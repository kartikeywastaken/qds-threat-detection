import pytest
from qds_protocol.measurement_record import MeasurementRecord

def test_validation():
    with pytest.raises(ValueError): MeasurementRecord(index=0,expected=2,observed=0,basis='Z',bell_bits=(0,0))
