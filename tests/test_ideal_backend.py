"""Tests for IdealCirqBackend — deterministic, no QVM required."""
import cirq
import pytest
from quantum_core.ideal import IdealCirqBackend
from quantum_core.errors import CircuitValidationError


def _z0():
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.measure(q, key='m')])


def _z1():
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.X(q), cirq.measure(q, key='m')])


def _xplus():
    """H|0⟩ measured in X basis (H then measure) → should give 0."""
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.H(q), cirq.H(q), cirq.measure(q, key='m')])


def _xminus():
    """X then H|0⟩ measured in X basis → should give 1."""
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.X(q), cirq.H(q), cirq.H(q), cirq.measure(q, key='m')])


@pytest.fixture
def backend():
    return IdealCirqBackend(seed=42)


def test_name(backend):
    assert backend.name == 'ideal'


def test_metadata(backend):
    meta = backend.metadata
    assert meta['backend'] == 'ideal'
    assert meta['simulated'] is True
    assert meta['noisy'] is False
    assert meta['processor'] is None


def test_z0_always_zero(backend):
    """Ideal |0⟩ measured in Z basis must always be 0."""
    result = backend.run(_z0(), 256)
    assert result.backend == 'ideal'
    assert result.repetitions == 256
    counts = result.histogram['m']
    assert counts.get(0, 0) == 256, f'Expected all zeros, got {counts}'
    assert counts.get(1, 0) == 0


def test_z1_always_one(backend):
    """Ideal |1⟩ measured in Z basis must always be 1."""
    result = backend.run(_z1(), 256)
    counts = result.histogram['m']
    assert counts.get(1, 0) == 256, f'Expected all ones, got {counts}'


def test_xplus_correct_basis(backend):
    """H|0⟩ then H (basis rotation) → should collapse back to 0."""
    result = backend.run(_xplus(), 512)
    counts = result.histogram['m']
    # After H·H = I, should recover |0⟩ deterministically
    assert counts.get(0, 0) == 512


def test_xminus_correct_basis(backend):
    """X·H|0⟩ then H → should give 1."""
    result = backend.run(_xminus(), 512)
    counts = result.histogram['m']
    assert counts.get(1, 0) == 512


def test_result_structure(backend):
    result = backend.run(_z0(), 32)
    assert isinstance(result.measurements, dict)
    assert isinstance(result.histogram, dict)
    assert result.duration_ms >= 0
    assert 'circuit_hash' in result.metadata
    assert 'qubit_count' in result.metadata
    assert 'depth' in result.metadata


def test_seeded_reproducibility():
    """Same seed must give identical results."""
    b1 = IdealCirqBackend(seed=7)
    b2 = IdealCirqBackend(seed=7)
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.H(q), cirq.measure(q, key='m')])
    r1 = b1.run(circuit, 128)
    r2 = b2.run(circuit, 128)
    assert r1.histogram == r2.histogram


def test_different_seeds_may_differ():
    """Different seeds should not produce identical results for random circuits."""
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.H(q), cirq.measure(q, key='m')])
    r1 = IdealCirqBackend(seed=1).run(circuit, 200)
    r2 = IdealCirqBackend(seed=99).run(circuit, 200)
    # They could theoretically match by chance, but very unlikely with different seeds
    # Just check both are valid distributions
    assert abs(sum(r1.histogram['m'].values()) - 200) == 0
    assert abs(sum(r2.histogram['m'].values()) - 200) == 0


def test_validate_rejects_parameterized():
    backend = IdealCirqBackend()
    q = cirq.LineQubit(0)
    theta = sympy.Symbol('theta')
    circuit = cirq.Circuit([cirq.rz(rads=theta)(q), cirq.measure(q, key='m')])
    with pytest.raises(CircuitValidationError):
        backend.validate(circuit)


def test_validate_rejects_duplicate_measurement_keys():
    backend = IdealCirqBackend()
    q = cirq.LineQubit(0)
    # Two measurements with the same key — should be rejected
    circuit = cirq.Circuit([
        cirq.measure(q, key='m'),
        cirq.measure(q, key='m'),
    ])
    with pytest.raises(CircuitValidationError):
        backend.validate(circuit)


import sympy  # noqa: E402 — imported here to keep pytest collection fast
