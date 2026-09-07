import pytest
from quantum_core.channel_noise_model import noise_model, calibration_metadata

def test_calibration():
    print('IBM calibration:',calibration_metadata())
    assert noise_model(0).is_ideal() and not noise_model(.5).is_ideal()
    with pytest.raises(ValueError): noise_model(-1)

def test_probe_noise_coverage():
    from quantum_core.channel_noise_model import homogeneous_model
    assert 'cx' in homogeneous_model(.5).noise_instructions
    assert homogeneous_model(0).is_ideal()
