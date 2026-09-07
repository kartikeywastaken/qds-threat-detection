"""Fast ideal Cirq execution, including mid-circuit measurement and feed-forward."""
import logging
import time
import cirq
from quantum_core.base import QuantumBackend, validate_input
from quantum_core.types import QuantumExecutionResult, normalize_result, circuit_hash, library_versions

LOGGER = logging.getLogger(__name__)


class IdealCirqBackend(QuantumBackend):
    """A new seeded sampler per call avoids history-dependent random streams."""
    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed

    @property
    def name(self) -> str:
        return 'ideal'

    @property
    def metadata(self) -> dict:
        return {'backend': self.name, 'processor': None, 'simulated': True, 'noisy': False,
                'display_name': 'Ideal Cirq Simulator', 'versions': library_versions(), 'compiler_version': 1}

    def validate(self, circuit: cirq.AbstractCircuit) -> None:
        validate_input(circuit)

    def run(self, circuit: cirq.AbstractCircuit, repetitions: int, *, seed: int | None = None) -> QuantumExecutionResult:
        validate_input(circuit, repetitions)
        actual_seed = self.seed if seed is None else seed
        start = time.perf_counter()
        result = cirq.Simulator(seed=actual_seed).run(cirq.Circuit(circuit), repetitions=repetitions)
        elapsed = (time.perf_counter() - start) * 1000
        metadata = {**self.metadata, 'seed': actual_seed, 'circuit_hash': circuit_hash(circuit),
                    'qubit_count': len(circuit.all_qubits()), 'depth': len(circuit),
                    'logical_to_physical': {str(q): str(q) for q in sorted(circuit.all_qubits())}}
        LOGGER.info('quantum_execution backend=ideal shots=%d qubits=%d depth=%d duration_ms=%.3f',
                    repetitions, metadata['qubit_count'], metadata['depth'], elapsed)
        return normalize_result(result, self.name, repetitions, elapsed, metadata)
