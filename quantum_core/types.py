"""Normalized result structures: no simulator objects cross the detection boundary."""
from dataclasses import dataclass, asdict
from collections import Counter
from importlib.metadata import version
from typing import Any
import hashlib
import cirq
import numpy as np
from quantum_core.errors import CircuitValidationError


def circuit_hash(circuit: cirq.AbstractCircuit) -> str:
    """Fingerprint deterministic Cirq JSON, including measurement key semantics."""
    return hashlib.sha256(cirq.to_json(cirq.Circuit(circuit)).encode()).hexdigest()


def library_versions() -> dict[str, str]:
    """Persist the installed runtime versions used in an experiment."""
    return {name: version(name) for name in ('cirq-core', 'cirq-google', 'qsimcirq', 'numpy')}


@dataclass(frozen=True)
class QuantumExecutionResult:
    """Each key contains one big-endian integer outcome per shot and its histogram."""
    backend: str
    repetitions: int
    measurements: dict[str, list[int]]
    histogram: dict[str, dict[int, int]]
    duration_ms: float
    metadata: dict[str, Any]

    def to_dict(self, include_measurements: bool = True) -> dict:
        """Normal telemetry can omit the per-shot arrays."""
        data = asdict(self)
        if not include_measurements:
            data.pop('measurements')
        return data


def normalize_result(result: cirq.Result, backend: str, repetitions: int,
                     duration_ms: float, metadata: dict) -> QuantumExecutionResult:
    """Flatten single measurement instances without reversing bit order."""
    measurements = {}
    widths = {}
    for key, array in result.records.items():
        if array.ndim != 3 or array.shape[:2] != (repetitions, 1):
            raise CircuitValidationError('Use a unique measurement key for every measurement instance')
        bits = np.asarray(array[:, 0, :], dtype=np.int64)
        if bits.shape[1] > 32 or not np.isin(bits, [0, 1]).all():
            raise CircuitValidationError('Only binary measurement keys up to 32 bits are supported')
        measurements[key] = (bits @ (2 ** np.arange(bits.shape[1] - 1, -1, -1))).tolist()
        widths[key] = bits.shape[1]
    if not measurements:
        raise CircuitValidationError('Execution requires at least one measurement')
    return QuantumExecutionResult(backend, repetitions, measurements,
                                  {key: dict(sorted(Counter(values).items())) for key, values in measurements.items()},
                                  duration_ms, {**metadata, 'measurement_widths': widths})


@dataclass(frozen=True)
class CompiledCircuit:
    """Immutable snapshots plus the initial logical-to-physical mapping."""
    original: cirq.FrozenCircuit
    compiled: cirq.FrozenCircuit
    qubit_map: dict[cirq.Qid, cirq.Qid]
    backend: str
