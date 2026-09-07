"""Compilation is independent of protocol construction, attacks and detection."""
import cirq
from quantum_core.base import validate_input
from quantum_core.types import CompiledCircuit
from quantum_core.device import compile_for_google_device
from quantum_core.errors import UnknownQuantumBackend


def compile_circuit(circuit: cirq.AbstractCircuit, backend) -> CompiledCircuit:
    """Return copies, preserving the original logical circuit exactly."""
    validate_input(circuit)
    original = cirq.FrozenCircuit(circuit)
    if backend.name == 'ideal':
        return CompiledCircuit(original, original, {q: q for q in original.all_qubits()}, 'ideal')
    if backend.name != 'qvm':
        raise UnknownQuantumBackend(f'No compiler for {backend.name}')
    compiled, mapping = compile_for_google_device(original, backend.device)
    return CompiledCircuit(original, compiled.freeze(), mapping, 'qvm')
