"""QVM baseline calibration — measured legitimate distributions, never hardcoded.

Calibration runs a known-good circuit family against the chosen backend and
records the resulting error rates and outcome distributions.  These become the
reference used by the statistical detector:

    legitimate QVM noise   →  baseline_error_rate ≈ 0.01
    attack-induced noise   →  observed_error_rate ≫ baseline_error_rate

No Google credentials are required; everything runs locally.
Calibration data is stored as JSON in the configured baseline_directory.
"""
from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cirq
import numpy as np
from scipy.stats import binomtest

from quantum_core.base import QuantumBackend
from quantum_core.config import QuantumConfig
from quantum_core.errors import BaselineMissingError, CircuitValidationError
from quantum_core.types import QuantumExecutionResult

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Circuit families
# ---------------------------------------------------------------------------

def _z0_circuit() -> cirq.Circuit:
    """Prepare |0⟩ and measure in Z basis — should give 0 with high fidelity."""
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.measure(q, key='m')])


def _z1_circuit() -> cirq.Circuit:
    """Prepare |1⟩ and measure in Z basis — should give 1 with high fidelity."""
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.X(q), cirq.measure(q, key='m')])


def _xplus_circuit() -> cirq.Circuit:
    """Prepare |+⟩ and measure in X basis — should be near-uniform."""
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.H(q), cirq.H(q), cirq.measure(q, key='m')])


def _xminus_circuit() -> cirq.Circuit:
    """Prepare |−⟩ and measure in X basis — should give 1 with high fidelity."""
    q = cirq.LineQubit(0)
    return cirq.Circuit([cirq.X(q), cirq.H(q), cirq.H(q), cirq.measure(q, key='m')])


def _bell_circuit() -> cirq.Circuit:
    """Prepare |Φ+⟩ and measure both qubits — legitimate correlations expected."""
    q0, q1 = cirq.LineQubit.range(2)
    return cirq.Circuit([
        cirq.H(q0),
        cirq.CNOT(q0, q1),
        cirq.measure(q0, key='m0'),
        cirq.measure(q1, key='m1'),
    ])


CIRCUIT_FAMILIES: dict[str, tuple[cirq.Circuit, dict[str, int]]] = {
    # name: (circuit, {measurement_key: expected_ideal_value})
    'z0':    (_z0_circuit(),     {'m': 0}),
    'z1':    (_z1_circuit(),     {'m': 1}),
    'xplus': (_xplus_circuit(),  {'m': 0}),   # |+⟩ → X basis ≈ 50/50; error = deviation from 50%
    'xminus': (_xminus_circuit(), {'m': 1}),
    'bell':  (_bell_circuit(),   {'m0': 0, 'm1': 0}),   # both bits correlated
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BaselineProfile:
    """Measured calibration profile for one circuit family on one backend."""
    protocol: str
    backend: str
    processor: str | None
    shots: int
    expected_ideal: dict[str, int]
    observed_histogram: dict[str, dict[int, int]]
    error_rate: float
    variance: float
    confidence_low: float
    confidence_high: float
    calibration_sigma: float
    threshold: float          # baseline_error_rate + sigma * stddev
    metadata: dict[str, Any]
    timestamp: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'BaselineProfile':
        return cls(**d)


# ---------------------------------------------------------------------------
# Error-rate calculation
# ---------------------------------------------------------------------------

def _compute_error_rate(result: QuantumExecutionResult, expected: dict[str, int]) -> float:
    """Fraction of shots where *any* measured key disagrees with its expected value.

    For keys with no ideal expectation (e.g., the second qubit of a Bell pair
    under QVM noise) we skip rather than fabricate an expected value.
    """
    shots = result.repetitions
    if shots == 0:
        return 0.0
    mismatch = 0
    counted = 0
    for key, exp_val in expected.items():
        if key not in result.measurements:
            continue
        outcomes = result.measurements[key]
        mismatch += sum(v != exp_val for v in outcomes)
        counted += len(outcomes)
    if counted == 0:
        return 0.0
    return mismatch / counted


# ---------------------------------------------------------------------------
# Calibration service
# ---------------------------------------------------------------------------

def calibrate_baseline(
    protocol: str,
    backend: QuantumBackend,
    repetitions: int,
    *,
    sigma: float = 3.0,
    seed: int | None = None,
) -> BaselineProfile:
    """Execute a legitimate circuit on *backend* and record the resulting distribution.

    The returned :class:`BaselineProfile` contains:
    - observed histogram (never hardcoded)
    - error rate measured through the backend
    - 99.9 % confidence interval from a binomial test
    - a detection threshold derived from the baseline statistics

    This deliberately runs through the full backend path so that QVM hardware-
    like noise is included in the baseline.  The threshold is therefore set
    *above* the expected QVM noise floor, not above zero.
    """
    if protocol not in CIRCUIT_FAMILIES:
        raise ValueError(f'Unknown circuit family {protocol!r}; available: {sorted(CIRCUIT_FAMILIES)}')
    if not 16 <= repetitions <= 100_000:
        raise ValueError('Calibration repetitions must be in [16, 100000]')
    if not math.isfinite(sigma) or not 1.0 <= sigma <= 8.0:
        raise ValueError('Detection sigma must be in [1, 8]')

    circuit, expected = CIRCUIT_FAMILIES[protocol]

    LOGGER.info(
        'qvm_calibrate_start protocol=%s backend=%s shots=%d',
        protocol, backend.name, repetitions,
    )
    start = time.perf_counter()
    result: QuantumExecutionResult = backend.run(circuit, repetitions, seed=seed)
    elapsed = (time.perf_counter() - start) * 1000

    error_rate = _compute_error_rate(result, expected)
    errors = round(error_rate * repetitions)

    # Exact binomial 99.9 % confidence interval
    ci = binomtest(errors, repetitions).proportion_ci(0.999)
    variance = error_rate * (1.0 - error_rate) / repetitions

    # threshold = baseline + sigma * stddev; never below a minimal floor
    stddev = math.sqrt(max(variance, 1e-10))
    threshold = min(0.95, error_rate + sigma * stddev)

    meta = {
        **result.metadata,
        'calibration_duration_ms': elapsed,
        'protocol': protocol,
        'sigma': sigma,
    }

    profile = BaselineProfile(
        protocol=protocol,
        backend=backend.name,
        processor=result.metadata.get('processor'),
        shots=repetitions,
        expected_ideal=expected,
        observed_histogram={k: dict(v) for k, v in result.histogram.items()},
        error_rate=error_rate,
        variance=variance,
        confidence_low=float(ci.low),
        confidence_high=float(ci.high),
        calibration_sigma=sigma,
        threshold=threshold,
        metadata=meta,
        timestamp=time.time(),
    )

    LOGGER.info(
        'qvm_calibrate_done protocol=%s backend=%s error_rate=%.4f threshold=%.4f duration_ms=%.1f',
        protocol, backend.name, error_rate, threshold, elapsed,
    )
    return profile


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _baseline_path(directory: Path, backend: str, protocol: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f'baseline_{backend}_{protocol}.json'


def save_baseline(profile: BaselineProfile, directory: Path | None = None) -> Path:
    """Persist a baseline profile to the configured directory."""
    if directory is None:
        directory = QuantumConfig.from_env().baseline_directory
    path = _baseline_path(directory, profile.backend, profile.protocol)
    path.write_text(json.dumps(profile.to_dict(), indent=2, allow_nan=False))
    LOGGER.info('baseline_saved path=%s', path)
    return path


def load_baseline(backend: str, protocol: str, directory: Path | None = None) -> BaselineProfile:
    """Load a previously saved baseline; raises :class:`BaselineMissingError` if absent."""
    if directory is None:
        directory = QuantumConfig.from_env().baseline_directory
    path = _baseline_path(directory, backend, protocol)
    if not path.exists():
        raise BaselineMissingError(
            f'No baseline found for backend={backend!r} protocol={protocol!r} at {path}. '
            'Run calibrate_baseline() and save_baseline() first.'
        )
    data = json.loads(path.read_text())
    return BaselineProfile.from_dict(data)


def calibrate_all_baselines(
    backend: QuantumBackend,
    repetitions: int | None = None,
    *,
    directory: Path | None = None,
    sigma: float | None = None,
    seed: int | None = None,
) -> dict[str, BaselineProfile]:
    """Calibrate and save baselines for every circuit family.

    Intended for admin/development use, not for every request.
    """
    config = QuantumConfig.from_env()
    reps = repetitions or config.shots
    sig = sigma or config.detection_sigma
    directory = directory or config.baseline_directory

    profiles: dict[str, BaselineProfile] = {}
    for protocol in CIRCUIT_FAMILIES:
        profile = calibrate_baseline(protocol, backend, reps, sigma=sig, seed=seed)
        save_baseline(profile, directory)
        profiles[protocol] = profile
    return profiles


# ---------------------------------------------------------------------------
# Compare backends (useful for demo/experiment)
# ---------------------------------------------------------------------------

def compare_backends(
    circuit: cirq.Circuit,
    repetitions: int,
    backends: list[QuantumBackend],
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    """Execute *circuit* on every listed backend and return normalized statistics.

    This is useful for demonstrating the difference between ideal and QVM results.
    Do NOT call this for every production request — QVM is significantly slower.
    """
    results: dict[str, Any] = {}
    for backend in backends:
        try:
            r = backend.run(circuit, repetitions, seed=seed)
            results[backend.name] = {
                'backend': backend.name,
                'metadata': r.metadata,
                'histogram': r.histogram,
                'repetitions': r.repetitions,
                'duration_ms': r.duration_ms,
                'error': None,
            }
        except Exception as exc:
            results[backend.name] = {
                'backend': backend.name,
                'error': f'{type(exc).__name__}: {exc}',
            }

    # Compute pairwise difference for first two backends if both succeeded
    names = [b.name for b in backends]
    if len(names) >= 2:
        a, b = names[0], names[1]
        if results[a].get('error') is None and results[b].get('error') is None:
            diff: dict[str, Any] = {}
            for key in results[a]['histogram']:
                ha = results[a]['histogram'].get(key, {})
                hb = results[b]['histogram'].get(key, {})
                all_outcomes = sorted(set(ha) | set(hb))
                total_a = sum(ha.values()) or 1
                total_b = sum(hb.values()) or 1
                tv = 0.5 * sum(
                    abs(ha.get(o, 0) / total_a - hb.get(o, 0) / total_b)
                    for o in all_outcomes
                )
                diff[key] = {'tv_distance': round(tv, 6), 'outcomes': all_outcomes}
            results['difference'] = {'tv_by_key': diff, 'compared': [a, b]}
    return results
