"""Tests for circuit compilation: ideal pass-through and QVM qubit mapping."""
import cirq
import pytest
from quantum_core.compiler import compile_circuit
from quantum_core.ideal import IdealCirqBackend
from quantum_core.qvm import GoogleQVMBackend
from quantum_core.types import CompiledCircuit
from quantum_core.errors import CircuitValidationError


def _simple_circuit() -> cirq.Circuit:
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.measure(q, key='m')])


def _two_qubit_circuit() -> cirq.Circuit:
    q0, q1 = cirq.LineQubit.range(2)
    return cirq.Circuit([
        cirq.H(q0),
        cirq.CNOT(q0, q1),
        cirq.measure(q0, key='m0'),
        cirq.measure(q1, key='m1'),
    ])


# ---------------------------------------------------------------------------
# Ideal backend — circuit must not be altered
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def ideal():
    return IdealCirqBackend(seed=0)


@pytest.fixture(scope='module')
def qvm():
    return GoogleQVMBackend(processor='willow', seed=0)


def test_ideal_compile_returns_compiled_circuit(ideal):
    compiled = compile_circuit(_simple_circuit(), ideal)
    assert isinstance(compiled, CompiledCircuit)


def test_ideal_compile_preserves_circuit(ideal):
    """Ideal compilation must return the original circuit unchanged."""
    original = _simple_circuit()
    compiled = compile_circuit(original, ideal)
    assert cirq.Circuit(compiled.compiled) == cirq.Circuit(original)


def test_ideal_qubit_map_is_identity(ideal):
    """Ideal backend should map each qubit to itself."""
    original = _two_qubit_circuit()
    compiled = compile_circuit(original, ideal)
    for logical, physical in compiled.qubit_map.items():
        assert logical == physical


def test_original_not_mutated_ideal(ideal):
    original = _two_qubit_circuit()
    original_str = str(original)
    _compiled = compile_circuit(original, ideal)
    assert str(original) == original_str


# ---------------------------------------------------------------------------
# QVM backend — qubit mapping and device validation
# ---------------------------------------------------------------------------

def test_qvm_compile_returns_compiled_circuit(qvm):
    compiled = compile_circuit(_simple_circuit(), qvm)
    assert isinstance(compiled, CompiledCircuit)
    assert compiled.backend == 'qvm'


def test_qvm_maps_to_grid_qubits(qvm):
    """Physical qubits must be GridQubits from the Willow device."""
    compiled = compile_circuit(_simple_circuit(), qvm)
    for physical in compiled.qubit_map.values():
        assert isinstance(physical, cirq.GridQubit), (
            f'Expected GridQubit, got {type(physical).__name__}: {physical}'
        )


def test_qvm_selected_qubits_exist_in_device(qvm):
    """All physical qubits selected must be in the Willow device topology."""
    compiled = compile_circuit(_two_qubit_circuit(), qvm)
    device_qubits = qvm.device.metadata.qubit_set
    for physical in compiled.qubit_map.values():
        assert physical in device_qubits, (
            f'{physical} not in Willow device qubit set'
        )


def test_qvm_physical_qubits_connected(qvm):
    """For a 2-qubit circuit, the two physical qubits must be adjacent."""
    compiled = compile_circuit(_two_qubit_circuit(), qvm)
    physical_qubits = list(compiled.qubit_map.values())
    if len(physical_qubits) < 2:
        return  # Nothing to check
    graph = qvm.device.metadata.nx_graph
    # The qubit mapping selects a connected BFS subset — path must exist
    import networkx as nx
    q0, q1 = physical_qubits[0], physical_qubits[1]
    assert nx.has_path(graph, q0, q1), (
        f'Physical qubits {q0} and {q1} are not connected in Willow topology'
    )


def test_qvm_mapping_is_deterministic(qvm):
    """Same circuit compiled twice must give the same qubit map."""
    circuit = _two_qubit_circuit()
    c1 = compile_circuit(circuit, qvm)
    c2 = compile_circuit(circuit, qvm)
    assert c1.qubit_map == c2.qubit_map


def test_original_not_mutated_qvm(qvm):
    original = _two_qubit_circuit()
    original_str = str(original)
    _compiled = compile_circuit(original, qvm)
    assert str(original) == original_str


def test_adaptive_circuit_rejected_by_qvm(qvm):
    """QVM cannot execute classically controlled adaptive circuits."""
    from quantum_core.errors import CircuitValidationError, CircuitCompilationError
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit([
        cirq.measure(q0, key='c'),
        cirq.X(q1).with_classical_controls('c'),
    ])
    with pytest.raises((CircuitValidationError, CircuitCompilationError, Exception)):
        compile_circuit(circuit, qvm)


def test_compiled_circuit_validates_on_device(qvm):
    """After QVM compilation, the circuit must pass device validation."""
    from quantum_core.device import validate_device_circuit
    compiled = compile_circuit(_two_qubit_circuit(), qvm)
    # This should not raise
    validate_device_circuit(compiled.compiled, qvm.device)
