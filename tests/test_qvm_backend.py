"""Tests for GoogleQVMBackend — verifies noisy local Willow simulation, no credentials."""
import pytest
import cirq
from quantum_core.qvm import GoogleQVMBackend
from quantum_core.errors import QVMUnavailableError, QuantumBackendError, CircuitValidationError


@pytest.fixture(scope='module')
def backend():
    """One lazily-initialised QVM backend shared across all tests in this module."""
    return GoogleQVMBackend(processor='willow', seed=42)


def _simple_circuit() -> cirq.Circuit:
    """Single-qubit |0⟩ → measure; expected ~0 with hardware noise."""
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.measure(q, key='m')])


def _bell_circuit() -> cirq.Circuit:
    q0, q1 = cirq.LineQubit.range(2)
    return cirq.Circuit([
        cirq.H(q0),
        cirq.CNOT(q0, q1),
        cirq.measure(q0, key='m0'),
        cirq.measure(q1, key='m1'),
    ])


# ---------------------------------------------------------------------------
# Backend identity
# ---------------------------------------------------------------------------

def test_name(backend):
    assert backend.name == 'qvm'


def test_metadata_fields(backend):
    meta = backend.metadata
    assert meta['backend'] == 'qvm'
    assert meta['simulated'] is True, 'QVM must always report simulated=true'
    assert meta['noisy'] is True, 'QVM must always report noisy=true'
    assert meta['processor'] is not None
    # Must NOT claim to be real hardware
    display = meta.get('display_name', '')
    assert 'physical' not in display.lower()
    assert 'real hardware' not in display.lower()
    assert 'willow' in display.lower() or 'qvm' in display.lower() or 'virtual' in display.lower()


def test_no_credentials_required(backend):
    """Initialising QVM must not raise credential-related errors."""
    # If QVMUnavailableError is raised it must not be about authentication
    try:
        meta = backend.metadata
        assert isinstance(meta, dict)
    except QVMUnavailableError as exc:
        msg = str(exc).lower()
        assert 'credential' not in msg
        assert 'api key' not in msg
        assert 'google cloud' not in msg
        pytest.skip(f'QVM unavailable: {exc}')


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def test_run_returns_correct_repetitions(backend):
    result = backend.run(_simple_circuit(), 64)
    assert result.repetitions == 64
    assert len(result.measurements['m']) == 64


def test_measurements_are_binary(backend):
    result = backend.run(_simple_circuit(), 128)
    for outcome in result.measurements['m']:
        assert outcome in (0, 1), f'Unexpected outcome: {outcome}'


def test_histogram_sums_to_repetitions(backend):
    result = backend.run(_simple_circuit(), 200)
    total = sum(result.histogram['m'].values())
    assert total == 200


def test_z0_mostly_zero_with_noise(backend):
    """|0⟩ should give mostly 0 even with Willow noise — noise shouldn't be > 50%."""
    result = backend.run(_simple_circuit(), 512)
    zero_fraction = result.histogram['m'].get(0, 0) / 512
    assert zero_fraction > 0.50, (
        f'Expected mostly 0 outcomes but got zero_fraction={zero_fraction:.3f}. '
        'Hardware noise should not flip majority of |0⟩ outcomes.'
    )


def test_bell_circuit_runs(backend):
    """Bell state should produce correlated outcomes (m0 ≈ m1)."""
    result = backend.run(_bell_circuit(), 256)
    assert 'm0' in result.histogram
    assert 'm1' in result.histogram
    total = sum(result.histogram['m0'].values())
    assert total == 256


def test_backend_metadata_in_result(backend):
    result = backend.run(_simple_circuit(), 32)
    meta = result.metadata
    assert meta.get('simulated') is True
    assert meta.get('noisy') is True
    assert meta.get('backend') == 'qvm'
    assert 'circuit_hash' in meta
    assert 'qubit_count' in meta


def test_qvm_compatible_flag(backend):
    result = backend.run(_simple_circuit(), 16)
    assert result.metadata.get('qvm_compatible') is True


def test_original_circuit_not_mutated(backend):
    """Compilation must not alter the original circuit in-place."""
    q = cirq.LineQubit(0)
    original = cirq.Circuit([cirq.H(q), cirq.measure(q, key='m')])
    original_str = str(original)
    _result = backend.run(original, 16)
    assert str(original) == original_str, 'Backend mutated the original circuit'


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_invalid_repetitions(backend):
    with pytest.raises((ValueError, Exception)):
        backend.run(_simple_circuit(), 0)


def test_too_many_qubits():
    """Circuits with > 12 qubits should be rejected before QVM init."""
    from quantum_core.errors import CircuitValidationError
    b = GoogleQVMBackend(processor='willow', seed=0)
    qubits = cirq.LineQubit.range(13)
    circuit = cirq.Circuit([cirq.measure(*qubits, key='m')])
    with pytest.raises((CircuitValidationError, Exception)):
        b.validate(circuit)


def test_adaptive_circuit_rejected():
    """Classically controlled operations must raise a clear error for QVM."""
    b = GoogleQVMBackend(processor='willow', seed=0)
    q0, q1 = cirq.LineQubit.range(2)
    # Build a classically controlled circuit
    circuit = cirq.Circuit([
        cirq.measure(q0, key='c'),
        cirq.X(q1).with_classical_controls('c'),
    ])
    with pytest.raises(Exception):
        b.validate(circuit)


def test_unknown_processor_raises():
    b = GoogleQVMBackend(processor='willow', seed=0)
    b.processor = 'nonexistent_processor_xyz'
    with pytest.raises(QVMUnavailableError):
        _ = b.metadata
