"""The shared Cirq circuit execution contract."""
from abc import ABC, abstractmethod
import cirq
from quantum_core.types import QuantumExecutionResult
from quantum_core.errors import CircuitValidationError


def validate_input(circuit: cirq.AbstractCircuit, repetitions: int = 1) -> None:
    """Reject ambiguous keys, unbound parameters and unbounded local workloads."""
    if not isinstance(circuit, cirq.AbstractCircuit):
        raise CircuitValidationError('Expected a Cirq circuit')
    if not isinstance(repetitions, int) or not 1 <= repetitions <= 100000:
        raise CircuitValidationError('Repetitions must be an integer in [1,100000]')
    if not 1 <= len(circuit.all_qubits()) <= 12:
        raise CircuitValidationError('Local execution supports 1–12 active qubits')
    if cirq.is_parameterized(circuit):
        raise CircuitValidationError('Resolve circuit parameters before execution')
    keys = [cirq.measurement_key_name(op) for op in circuit.all_operations() if cirq.is_measurement(op)]
    if not keys or len(keys) != len(set(keys)):
        raise CircuitValidationError('Measurements require nonempty, unique keys')


class QuantumBackend(ABC):
    """Application execution interface; construction must be cheap."""
    @property
    @abstractmethod
    def name(self) -> str:
        """Stable backend identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def metadata(self) -> dict:
        """Public execution identity, including whether simulation is noisy."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, circuit: cirq.AbstractCircuit) -> None:
        """Validate a logical input circuit."""
        raise NotImplementedError

    @abstractmethod
    def run(self, circuit: cirq.AbstractCircuit, repetitions: int, *, seed: int | None = None) -> QuantumExecutionResult:
        """Execute a logical circuit and normalize measurements."""
        raise NotImplementedError
