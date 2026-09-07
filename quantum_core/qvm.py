"""Google Quantum Virtual Machine — noisy virtual Willow processor, entirely local."""
from functools import lru_cache
from threading import RLock
import hashlib
import logging
import time
import cirq
from quantum_core.base import QuantumBackend, validate_input
from quantum_core.errors import QVMUnavailableError, QuantumBackendError
from quantum_core.types import QuantumExecutionResult, circuit_hash, library_versions, normalize_result

LOGGER = logging.getLogger(__name__)


class _SeededQSimSampler(cirq.Sampler):
    """Keep Google's noise model and reinitialize only the cheap shot RNG per job."""
    def __init__(self, noise, seed: int | None = None) -> None:
        import qsimcirq
        self.noise = noise; self.seed = seed; self.simulator_class = qsimcirq.QSimSimulator

    def run_sweep(self, program, params, repetitions=1):
        sampler = self.simulator_class(noise=self.noise, seed=self.seed, qsim_options={'t': 1})
        return sampler.run_sweep(program, params, repetitions=repetitions)


class GoogleQVMBackend(QuantumBackend):
    """Lazy official local engine with explicit qsim execution and no ideal fallback."""
    def __init__(self, processor: str = 'willow', seed: int | None = None) -> None:
        self.processor = 'willow_pink' if processor == 'willow' else processor
        self.seed = seed; self._engine = None; self._device = None
        self._sampler = None; self._calibration_metadata = {}; self._lock = RLock()

    @property
    def name(self) -> str:
        return 'qvm'

    def _initialize(self) -> None:
        with self._lock:
            if self._engine is not None:
                return
            try:
                import qsimcirq
                import cirq_google as cg
                if self.processor != 'willow_pink':
                    raise ValueError(f'Unsupported virtual Willow processor {self.processor!r}')
                # Supplying a simulator class prevents Google's factory's optional ideal fallback.
                samplers = []
                def sampler_factory(**kwargs):
                    sampler = _SeededQSimSampler(**kwargs); samplers.append(sampler); return sampler
                engine = cg.engine.create_default_noisy_quantum_virtual_machine(
                    processor_id=self.processor, simulator_class=sampler_factory, seed=self.seed)
                calibration = cg.engine.load_median_device_calibration(self.processor)
                metadata = {'calibration_timestamp_ms': calibration.timestamp,
                            'noise_fingerprint': hashlib.sha256(cirq.to_json(calibration).encode()).hexdigest(),
                            'noise_model': type(samplers[0].noise).__name__,
                            'simulator': f'qsimcirq.QSimSimulator {qsimcirq.__version__}'}
                device = engine.get_processor(self.processor).get_device()
            except Exception as exc:
                # Boundary translation preserves the cause; execution never continues after failure.
                raise QVMUnavailableError('Google QVM backend could not be initialized. '
                                          'Check cirq-google/qsimcirq installation and bundled Willow templates. '
                                          f'Cause: {type(exc).__name__}: {exc}') from exc
            self._engine = engine; self._device = device; self._sampler = samplers[0]
            self._calibration_metadata = metadata
            LOGGER.info('quantum_backend_initialized backend=qvm processor=%s simulated=true noisy=true', self.processor)

    @property
    def device(self):
        self._initialize()
        return self._device

    @property
    def metadata(self) -> dict:
        self._initialize()
        return {'backend': 'qvm', 'processor': self.processor, 'simulated': True, 'noisy': True,
                'display_name': 'Google Quantum Virtual Machine — noisy virtual Willow processor',
                'versions': library_versions(), 'compiler_version': 1, **self._calibration_metadata}

    @lru_cache(maxsize=256)
    def _compile(self, circuit: cirq.FrozenCircuit):
        from quantum_core.compiler import compile_circuit
        return compile_circuit(circuit, self)

    def validate(self, circuit: cirq.AbstractCircuit) -> None:
        validate_input(circuit)
        self._compile(cirq.FrozenCircuit(circuit))

    def run(self, circuit: cirq.AbstractCircuit, repetitions: int, *, seed: int | None = None) -> QuantumExecutionResult:
        validate_input(circuit, repetitions)
        compiled = self._compile(cirq.FrozenCircuit(circuit))
        actual_seed = self.seed if seed is None else seed
        with self._lock:
            self._sampler.seed = actual_seed
            start = time.perf_counter()
            try:
                result = self._engine.get_sampler(self.processor).run(cirq.Circuit(compiled.compiled), repetitions=repetitions)
            except Exception as exc:
                raise QuantumBackendError(f'Local Willow QVM execution failed: {type(exc).__name__}: {exc}') from exc
            elapsed = (time.perf_counter() - start) * 1000
        metadata = {**self.metadata, 'seed': actual_seed, 'circuit_hash': circuit_hash(compiled.original),
                    'compiled_circuit_hash': circuit_hash(compiled.compiled),
                    'logical_to_physical': {str(k): str(v) for k, v in compiled.qubit_map.items()},
                    'qubit_count': len(compiled.compiled.all_qubits()), 'depth': len(compiled.compiled),
                    'qvm_compatible': True}
        LOGGER.info('quantum_execution backend=qvm processor=%s shots=%d qubits=%d depth=%d duration_ms=%.3f',
                    self.processor, repetitions, metadata['qubit_count'], metadata['depth'], elapsed)
        return normalize_result(result, self.name, repetitions, elapsed, metadata)
