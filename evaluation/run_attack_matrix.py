"""Ideal-vs-QVM attack matrix experiment runner.

Executes every attack scenario against both the ideal Cirq simulator and the
Google Quantum Virtual Machine (noisy virtual Willow processor) and reports
the resulting measurement distributions and detection statistics.

Usage:
    .venv/bin/python evaluation/run_attack_matrix.py
    .venv/bin/python evaluation/run_attack_matrix.py --backend ideal --shots 1000
    .venv/bin/python evaluation/run_attack_matrix.py --backend qvm   --shots 2000
    .venv/bin/python evaluation/run_attack_matrix.py --compare        --shots 500
    .venv/bin/python evaluation/run_attack_matrix.py --output artifacts/matrix --shots 2000

QVM NOTE: The QVM (Google Quantum Virtual Machine) is a LOCAL noisy simulation
of a virtual Google Willow processor.  It does NOT execute on physical quantum
hardware and requires no Google credentials.

The ideal backend is used for:
  - fast unit tests
  - reference / comparison baseline
  - deterministic debugging

The QVM backend is used for:
  - hardware-like noise modelling
  - realistic DPM experimental results
  - processor-oriented circuit constraints
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running as a script from the project root
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cirq
import numpy as np

from quantum_core.factory import get_quantum_backend
from quantum_core.calibration import calibrate_baseline, CIRCUIT_FAMILIES
from quantum_core.types import QuantumExecutionResult
from detection_engine.statistics import compare_with_baseline, total_variation_distance

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

# We define lightweight Cirq-native circuits to run through the Cirq backends
# (ideal / QVM).  These are complementary to the Qiskit-based teleportation
# scenarios in run_full_evaluation.py.  Both layers coexist.

def _build_legitimate_circuit() -> tuple[cirq.Circuit, str, dict[str, int]]:
    """|0⟩ prepared and measured — ideal = always 0."""
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.measure(q, key='m')])
    return circuit, 'legitimate', {'m': 0}


def _build_pauli_x_circuit() -> tuple[cirq.Circuit, str, dict[str, int]]:
    """Pauli-X attack: flips |0⟩ → |1⟩ — ideal = always 1, detector should flag."""
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.X(q), cirq.measure(q, key='m')])
    return circuit, 'pauli_x', {'m': 0}   # expected_ideal is still 0 (from honest prep)


def _build_pauli_z_circuit() -> tuple[cirq.Circuit, str, dict[str, int]]:
    """Pauli-Z attack: phase flip on |+⟩ → |−⟩ — measured in Z basis shows 50/50."""
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.H(q), cirq.Z(q), cirq.H(q), cirq.measure(q, key='m')])
    return circuit, 'pauli_z', {'m': 0}


def _build_pauli_y_circuit() -> tuple[cirq.Circuit, str, dict[str, int]]:
    """Pauli-Y attack: both phase and bit flip."""
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit([cirq.Y(q), cirq.measure(q, key='m')])
    return circuit, 'pauli_y', {'m': 0}


def _build_hadamard_intercept_circuit() -> tuple[cirq.Circuit, str, dict[str, int]]:
    """Intercept-resend with random-basis measurement: introduces ~50% QBER."""
    q = cirq.LineQubit(0)
    # Attacker measures in wrong basis (H rotates to X basis) then re-prepares
    circuit = cirq.Circuit([cirq.H(q), cirq.H(q), cirq.measure(q, key='m')])
    return circuit, 'intercept_resend', {'m': 0}


def _build_depolarizing_circuit() -> tuple[cirq.Circuit, str, dict[str, int]]:
    """Simulate channel manipulation via explicit depolarizing noise injection."""
    q = cirq.LineQubit(0)
    # Mix X+Y+Z at equal probability — approximates strong channel noise
    circuit = cirq.Circuit([
        cirq.X(q) ** 0.33,
        cirq.Y(q) ** 0.33,
        cirq.measure(q, key='m'),
    ])
    return circuit, 'channel_manipulation', {'m': 0}


def _build_bell_forgery_circuit() -> tuple[cirq.Circuit, str, dict[str, int]]:
    """Forger tries to reproduce Bell state without knowing the secret key."""
    q0, q1 = cirq.LineQubit.range(2)
    # Forger guesses wrong basis: sends |11⟩ instead of |Φ+⟩
    circuit = cirq.Circuit([
        cirq.X(q0),
        cirq.X(q1),
        cirq.measure(q0, key='m0'),
        cirq.measure(q1, key='m1'),
    ])
    return circuit, 'forgery', {'m0': 0, 'm1': 0}


SCENARIOS: list[tuple[cirq.Circuit, str, dict[str, int]]] = [
    _build_legitimate_circuit(),
    _build_pauli_x_circuit(),
    _build_pauli_y_circuit(),
    _build_pauli_z_circuit(),
    _build_hadamard_intercept_circuit(),
    _build_depolarizing_circuit(),
    _build_bell_forgery_circuit(),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_attack_matrix(
    backend_names: list[str],
    shots: int = 2000,
    seed: int | None = None,
    calibration_shots: int | None = None,
) -> dict:
    """Run all attack scenarios against the specified backends.

    Returns a dict with 'results' (list of per-scenario rows) and 'summary'.
    """
    cal_shots = calibration_shots or max(shots, 512)
    rows = []

    for backend_name in backend_names:
        print(f'\n{"="*60}', flush=True)
        print(f'Backend: {backend_name}', flush=True)
        print(f'{"="*60}', flush=True)

        try:
            backend = get_quantum_backend(backend_name, seed=seed)
        except Exception as exc:
            print(f'  ERROR initialising backend {backend_name}: {exc}', flush=True)
            rows.append({'backend': backend_name, 'error': str(exc)})
            continue

        # Calibrate legitimate baseline using 'z0' circuit family
        print(f'  Calibrating legitimate baseline ({cal_shots} shots)...', flush=True)
        t0 = time.perf_counter()
        try:
            baseline = calibrate_baseline('z0', backend, cal_shots, seed=seed)
        except Exception as exc:
            print(f'  ERROR during calibration: {exc}', flush=True)
            rows.append({'backend': backend_name, 'error': f'calibration: {exc}'})
            continue
        cal_time = (time.perf_counter() - t0) * 1000
        print(f'  Baseline error_rate={baseline.error_rate:.4f} '
              f'threshold={baseline.threshold:.4f} ({cal_time:.0f}ms)', flush=True)

        # Run each attack scenario
        for circuit, scenario, expected_ideal in SCENARIOS:
            t1 = time.perf_counter()
            try:
                result: QuantumExecutionResult = backend.run(circuit, shots, seed=seed)
            except Exception as exc:
                print(f'  SCENARIO {scenario}: ERROR {exc}', flush=True)
                rows.append({
                    'backend': backend_name,
                    'scenario': scenario,
                    'error': str(exc),
                })
                continue
            elapsed = (time.perf_counter() - t1) * 1000

            # Compute observed error rate against ideal expected values
            total = shots
            mismatches = 0
            for key, exp_val in expected_ideal.items():
                if key in result.measurements:
                    mismatches += sum(v != exp_val for v in result.measurements[key])
            observed_error = mismatches / total if total else 0.0

            # Compare against calibrated baseline
            stats = compare_with_baseline(
                observed_histogram=result.histogram,
                baseline_histogram=baseline.observed_histogram,
                baseline_error_rate=baseline.error_rate,
                baseline_threshold=baseline.threshold,
                baseline_sigma=baseline.calibration_sigma,
                expected_ideal=expected_ideal,
            )

            row = {
                'backend': backend_name,
                'scenario': scenario,
                'shots': shots,
                'expected_ideal': expected_ideal,
                'histogram': result.histogram,
                'observed_error_rate': round(observed_error, 6),
                'baseline_error_rate': round(baseline.error_rate, 6),
                'baseline_threshold': round(baseline.threshold, 6),
                'delta': round(observed_error - baseline.error_rate, 6),
                'tv_distance': round(stats['mean_tv_distance'], 6),
                'classification': stats['classification'],
                'reason': stats['reason'],
                'duration_ms': round(elapsed, 1),
                'backend_metadata': {
                    'processor': result.metadata.get('processor'),
                    'simulated': result.metadata.get('simulated'),
                    'noisy': result.metadata.get('noisy'),
                    'display_name': result.metadata.get('display_name'),
                },
            }
            rows.append(row)

            flag = '⚠️ ' if stats['classification'] == 'attack' else (
                   '❓ ' if stats['classification'] == 'suspicious' else '✓  ')
            print(
                f'  {flag}{scenario:<26} '
                f'err={observed_error:.4f}  '
                f'delta={observed_error - baseline.error_rate:+.4f}  '
                f'tv={stats["mean_tv_distance"]:.4f}  '
                f'{stats["classification"]:<12}  '
                f'({elapsed:.0f}ms)',
                flush=True,
            )

    # Aggregate by scenario across backends
    summary: dict = {
        'backends': backend_names,
        'shots': shots,
        'calibration_shots': cal_shots,
        'total_scenarios': len(SCENARIOS),
        'rows': len(rows),
        'attack_flags': sum(1 for r in rows if r.get('classification') == 'attack'),
        'suspicious_flags': sum(1 for r in rows if r.get('classification') == 'suspicious'),
        'legitimate_flags': sum(1 for r in rows if r.get('classification') == 'legitimate'),
        'errors': sum(1 for r in rows if 'error' in r),
        'note': (
            'QVM is a noisy virtual Willow processor running locally — '
            'it is NOT physical quantum hardware.'
        ),
    }

    return {'results': rows, 'summary': summary}


def print_table(rows: list[dict]) -> None:
    """Print a human-readable table of results."""
    print()
    print(f"{'Backend':<8} {'Scenario':<26} {'Error':>8} {'Delta':>8} {'TV':>6} {'Class':<12}")
    print('-' * 74)
    for r in rows:
        if 'error' in r:
            print(f"  {'ERROR':<8} {r.get('scenario','?'):<26} {r['error']}")
            continue
        print(
            f"  {r['backend']:<8} "
            f"{r['scenario']:<26} "
            f"{r['observed_error_rate']:>8.4f} "
            f"{r['delta']:>+8.4f} "
            f"{r['tv_distance']:>6.4f} "
            f"{r['classification']:<12}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--backend', choices=['ideal', 'qvm', 'both'], default='both',
        help='Which backend(s) to run (default: both)',
    )
    parser.add_argument(
        '--compare', action='store_true',
        help='Run both backends and produce a side-by-side comparison (shorthand for --backend both)',
    )
    parser.add_argument('--shots', type=int, default=2000, help='Shots per scenario (default: 2000)')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    parser.add_argument(
        '--output', type=Path, default=Path('artifacts/attack_matrix'),
        help='Output directory for JSON results (default: artifacts/attack_matrix)',
    )
    args = parser.parse_args()

    backend_names = (
        ['ideal', 'qvm'] if (args.compare or args.backend == 'both')
        else [args.backend]
    )

    print(f'DPM Attack Matrix — {", ".join(backend_names)} backend(s)')
    print(f'Shots per scenario: {args.shots}')
    if 'qvm' in backend_names:
        print('QVM: Google Quantum Virtual Machine — noisy virtual Willow processor (local, no credentials)')
    print()

    report = run_attack_matrix(backend_names, shots=args.shots, seed=args.seed)

    print_table(report['results'])

    print('\nSummary:')
    for k, v in report['summary'].items():
        if k not in ('note',):
            print(f'  {k}: {v}')
    print(f"  NOTE: {report['summary']['note']}")

    args.output.mkdir(parents=True, exist_ok=True)
    out_path = args.output / 'attack_matrix.json'
    out_path.write_text(json.dumps(report, indent=2, allow_nan=False))
    print(f'\nResults written to: {out_path}')


if __name__ == '__main__':
    main()
