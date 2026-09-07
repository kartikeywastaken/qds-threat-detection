"""Tests for QVM baseline calibration."""
import math
import pytest
import cirq
from quantum_core.ideal import IdealCirqBackend
from quantum_core.calibration import (
    calibrate_baseline,
    CIRCUIT_FAMILIES,
    BaselineProfile,
    compare_backends,
)
from quantum_core.errors import BaselineMissingError


@pytest.fixture(scope='module')
def ideal():
    return IdealCirqBackend(seed=42)


# ---------------------------------------------------------------------------
# Calibration structure
# ---------------------------------------------------------------------------

def test_calibrate_returns_baseline_profile(ideal):
    profile = calibrate_baseline('z0', ideal, repetitions=128, seed=42)
    assert isinstance(profile, BaselineProfile)


def test_profile_contains_shot_count(ideal):
    profile = calibrate_baseline('z0', ideal, repetitions=64, seed=42)
    assert profile.shots == 64


def test_profile_probabilities_sum_to_one(ideal):
    """All histogram counts should sum to the number of shots."""
    profile = calibrate_baseline('z0', ideal, repetitions=128, seed=42)
    for key, hist in profile.observed_histogram.items():
        total = sum(hist.values())
        assert total == 128, f'Key {key}: expected 128 shots, got {total}'


def test_backend_metadata_retained(ideal):
    profile = calibrate_baseline('z0', ideal, repetitions=64, seed=42)
    assert profile.backend == 'ideal'
    assert profile.processor is None or isinstance(profile.processor, str)


def test_error_rate_is_finite(ideal):
    profile = calibrate_baseline('z0', ideal, repetitions=128, seed=42)
    assert math.isfinite(profile.error_rate)
    assert 0.0 <= profile.error_rate <= 1.0


def test_confidence_interval_valid(ideal):
    profile = calibrate_baseline('z0', ideal, repetitions=256, seed=42)
    assert profile.confidence_low <= profile.error_rate <= profile.confidence_high
    assert profile.confidence_low >= 0.0
    assert profile.confidence_high <= 1.0


def test_threshold_above_baseline(ideal):
    """Threshold must be at least as high as the measured error rate."""
    profile = calibrate_baseline('z0', ideal, repetitions=256, seed=42)
    assert profile.threshold >= profile.error_rate


def test_ideal_z0_error_rate_near_zero(ideal):
    """Ideal |0⟩ → measure should give zero errors (ideal simulator, no noise)."""
    profile = calibrate_baseline('z0', ideal, repetitions=512, seed=42)
    assert profile.error_rate == 0.0, (
        f'Ideal z0 baseline should have 0% error, got {profile.error_rate:.4f}'
    )


def test_all_circuit_families_calibrate(ideal):
    """Every registered circuit family must complete without error."""
    for protocol in CIRCUIT_FAMILIES:
        profile = calibrate_baseline(protocol, ideal, repetitions=64, seed=42)
        assert profile.protocol == protocol


def test_unknown_protocol_raises(ideal):
    with pytest.raises(ValueError, match='Unknown circuit family'):
        calibrate_baseline('nonexistent_protocol_xyz', ideal, repetitions=64)


def test_invalid_repetitions_raises(ideal):
    with pytest.raises(ValueError, match='repetitions'):
        calibrate_baseline('z0', ideal, repetitions=5)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip(ideal, tmp_path):
    from quantum_core.calibration import save_baseline, load_baseline
    profile = calibrate_baseline('z0', ideal, repetitions=64, seed=1)
    save_baseline(profile, directory=tmp_path)
    loaded = load_baseline('ideal', 'z0', directory=tmp_path)
    assert loaded.protocol == profile.protocol
    assert loaded.backend == profile.backend
    assert loaded.shots == profile.shots
    assert abs(loaded.error_rate - profile.error_rate) < 1e-10


def test_load_missing_baseline_raises(tmp_path):
    from quantum_core.calibration import load_baseline
    with pytest.raises(BaselineMissingError):
        load_baseline('ideal', 'z0', directory=tmp_path)


# ---------------------------------------------------------------------------
# compare_backends
# ---------------------------------------------------------------------------

def test_compare_backends_returns_both(ideal):
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.measure(q, key='m')])
    result = compare_backends(circuit, 32, [ideal, ideal])
    assert 'ideal' in result


def test_compare_backends_includes_tv_distance(ideal):
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.measure(q, key='m')])
    result = compare_backends(circuit, 64, [ideal, ideal])
    if 'difference' in result:
        diff = result['difference']
        assert 'tv_by_key' in diff
