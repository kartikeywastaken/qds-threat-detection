"""Tests for the quantum backend factory."""
import pytest
from quantum_core.factory import get_quantum_backend
from quantum_core.ideal import IdealCirqBackend
from quantum_core.qvm import GoogleQVMBackend
from quantum_core.errors import UnknownQuantumBackend


def test_ideal_returns_ideal_backend():
    backend = get_quantum_backend('ideal')
    assert isinstance(backend, IdealCirqBackend)
    assert backend.name == 'ideal'


def test_qvm_returns_qvm_backend():
    backend = get_quantum_backend('qvm')
    assert isinstance(backend, GoogleQVMBackend)
    assert backend.name == 'qvm'


def test_unknown_backend_raises():
    with pytest.raises(UnknownQuantumBackend):
        get_quantum_backend('unknown_backend_xyz')


def test_engine_raises_not_implemented():
    """Engine backend is reserved but not implemented."""
    with pytest.raises(UnknownQuantumBackend):
        get_quantum_backend('engine')


def test_ideal_backend_is_cached():
    """Factory must return the same object for the same params (lru_cache)."""
    b1 = get_quantum_backend('ideal', seed=42)
    b2 = get_quantum_backend('ideal', seed=42)
    assert b1 is b2


def test_qvm_backend_is_cached():
    b1 = get_quantum_backend('qvm', seed=1)
    b2 = get_quantum_backend('qvm', seed=1)
    assert b1 is b2


def test_seeded_ideal_is_different_from_unseeded():
    b_seeded = get_quantum_backend('ideal', seed=7)
    b_default = get_quantum_backend('ideal')
    # They may differ in seed value but both are IdealCirqBackend
    assert isinstance(b_seeded, IdealCirqBackend)
    assert isinstance(b_default, IdealCirqBackend)


def test_ideal_metadata():
    b = get_quantum_backend('ideal')
    meta = b.metadata
    assert meta['simulated'] is True
    assert meta['noisy'] is False


def test_qvm_metadata():
    b = get_quantum_backend('qvm')
    meta = b.metadata
    assert meta['simulated'] is True
    assert meta['noisy'] is True
    assert meta['backend'] == 'qvm'
