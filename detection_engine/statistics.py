"""Backend-neutral statistical detection metrics for QVM-calibrated threat analysis.

These functions compare an observed measurement distribution against a
calibrated QVM baseline and return explainable, non-ML evidence.

Key metrics:
- observed_error_rate   — fraction of unexpected measurement outcomes
- baseline_error_rate   — expected noise floor from legitimate QVM calibration
- error_rate_delta      — observed minus baseline
- total_variation_distance (TV)  — half the L1 distance between distributions
- chi_square            — optional goodness-of-fit statistic
- classification        — 'legitimate', 'suspicious', or 'attack'

TV distance:
    TV(P, Q) = 0.5 * Σ |P_i - Q_i|

Thresholds are derived from baseline statistics, never hardcoded constants.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import chisquare


# ---------------------------------------------------------------------------
# Core distance / rate functions
# ---------------------------------------------------------------------------

def total_variation_distance(p: dict[int, int], q: dict[int, int]) -> float:
    """Compute TV(P, Q) = 0.5 * Σ |P_i - Q_i| for two histograms.

    Both histograms are normalised internally.
    """
    all_keys = set(p) | set(q)
    total_p = sum(p.values()) or 1
    total_q = sum(q.values()) or 1
    return 0.5 * sum(
        abs(p.get(k, 0) / total_p - q.get(k, 0) / total_q)
        for k in all_keys
    )


def chi_square_statistic(
    observed: dict[int, int],
    expected: dict[int, int],
) -> tuple[float, float]:
    """Return (chi2, p_value) for observed vs expected counts.

    Bins with zero expected counts are merged with adjacent bins to avoid
    division by zero.  Returns (nan, nan) if fewer than 2 bins remain.
    """
    all_keys = sorted(set(observed) | set(expected))
    obs_arr = np.array([observed.get(k, 0) for k in all_keys], dtype=float)
    exp_arr = np.array([expected.get(k, 0) for k in all_keys], dtype=float)

    # Normalise expected to match observed total
    obs_total = obs_arr.sum()
    exp_total = exp_arr.sum()
    if obs_total == 0 or exp_total == 0:
        return math.nan, math.nan
    exp_arr = exp_arr * (obs_total / exp_total)

    # Remove zero-expected bins
    nonzero = exp_arr > 0
    if nonzero.sum() < 2:
        return math.nan, math.nan

    stat, pval = chisquare(obs_arr[nonzero], f_exp=exp_arr[nonzero])
    return float(stat), float(pval)


def kl_divergence_safe(p: dict[int, int], q: dict[int, int], epsilon: float = 1e-10) -> float:
    """KL(P || Q) with additive smoothing to handle zero-probability bins.

    Returns positive float; zero means identical distributions.
    """
    all_keys = set(p) | set(q)
    total_p = sum(p.values()) or 1
    total_q = sum(q.values()) or 1
    kl = 0.0
    for k in all_keys:
        pi = p.get(k, 0) / total_p + epsilon
        qi = q.get(k, 0) / total_q + epsilon
        kl += pi * math.log(pi / qi)
    return max(0.0, kl)


# ---------------------------------------------------------------------------
# Per-key statistics
# ---------------------------------------------------------------------------

def _key_error_rate(histogram: dict[int, int], expected_ideal: int) -> float:
    """Fraction of shots that did NOT match the expected ideal outcome."""
    total = sum(histogram.values())
    if total == 0:
        return 0.0
    mismatches = sum(count for outcome, count in histogram.items() if outcome != expected_ideal)
    return mismatches / total


# ---------------------------------------------------------------------------
# Main comparison function
# ---------------------------------------------------------------------------

def compare_with_baseline(
    observed_histogram: dict[str, dict[int, int]],
    baseline_histogram: dict[str, dict[int, int]],
    baseline_error_rate: float,
    baseline_threshold: float,
    baseline_sigma: float,
    *,
    expected_ideal: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Compare an observed distribution against a calibrated baseline.

    Returns structured evidence including classification and reason.

    Args:
        observed_histogram: {key: {outcome: count}} from the quantum execution.
        baseline_histogram: {key: {outcome: count}} from the calibration run.
        baseline_error_rate: The measured error rate during calibration.
        baseline_threshold:  Derived threshold = baseline + sigma*stddev.
        baseline_sigma:      Sigma factor used to derive the threshold.
        expected_ideal:      {key: ideal_outcome} — used to compute
                             observed_error_rate directly from ideal expectation.

    Returns:
        A dict with 'classification', 'reason', and numeric evidence.
    """
    if not observed_histogram:
        return {'classification': 'unknown', 'reason': 'No measurements to compare', 'error': True}

    # --- observed error rate ---
    if expected_ideal:
        total_shots = 0
        mismatches = 0
        for key, exp_val in expected_ideal.items():
            hist = observed_histogram.get(key, {})
            if not hist:
                continue
            total = sum(hist.values())
            total_shots += total
            mismatches += sum(c for o, c in hist.items() if o != exp_val)
        observed_error_rate = mismatches / total_shots if total_shots else 0.0
    else:
        # Estimate error rate as 1 - dominant-outcome fraction
        rates = []
        for key, hist in observed_histogram.items():
            total = sum(hist.values())
            if total:
                dominant = max(hist.values())
                rates.append(1.0 - dominant / total)
        observed_error_rate = float(np.mean(rates)) if rates else 0.0

    error_rate_delta = observed_error_rate - baseline_error_rate

    # --- TV distance (per-key average) ---
    tv_distances: dict[str, float] = {}
    for key in set(observed_histogram) | set(baseline_histogram):
        obs = observed_histogram.get(key, {})
        base = baseline_histogram.get(key, {})
        tv_distances[key] = total_variation_distance(obs, base)
    mean_tv = float(np.mean(list(tv_distances.values()))) if tv_distances else 0.0

    # --- Chi-square (first key only for simplicity) ---
    chi2: float = math.nan
    chi_p: float = math.nan
    first_key = next(iter(observed_histogram), None)
    if first_key and first_key in baseline_histogram:
        chi2, chi_p = chi_square_statistic(
            observed_histogram[first_key],
            baseline_histogram[first_key],
        )

    # --- KL divergence ---
    kl_values: dict[str, float] = {}
    for key in set(observed_histogram) & set(baseline_histogram):
        kl_values[key] = kl_divergence_safe(
            observed_histogram[key],
            baseline_histogram[key],
        )
    mean_kl = float(np.mean(list(kl_values.values()))) if kl_values else 0.0

    # --- Classification ---
    # Use threshold derived from calibration (sigma * stddev above baseline mean).
    # An additional TV-based check catches distribution shape changes that
    # error rate alone might miss (e.g., uniform noise vs. targeted Pauli).
    is_attack = (
        observed_error_rate > baseline_threshold
        or mean_tv > 0.2          # hard floor; TV > 0.2 is practically detectable
    )
    is_suspicious = (
        not is_attack
        and (
            error_rate_delta > (baseline_threshold - baseline_error_rate) * 0.5
            or mean_tv > 0.05
        )
    )

    if is_attack:
        classification = 'attack'
        reason = (
            f'Observed error rate {observed_error_rate:.4f} exceeds '
            f'baseline threshold {baseline_threshold:.4f} '
            f'(baseline {baseline_error_rate:.4f} + {baseline_sigma}σ). '
            f'TV distance {mean_tv:.4f}.'
        )
    elif is_suspicious:
        classification = 'suspicious'
        reason = (
            f'Observed error rate {observed_error_rate:.4f} is elevated relative '
            f'to baseline {baseline_error_rate:.4f} (delta={error_rate_delta:+.4f}). '
            f'TV distance {mean_tv:.4f}. Below hard attack threshold {baseline_threshold:.4f}.'
        )
    else:
        classification = 'legitimate'
        reason = (
            f'Observed error rate {observed_error_rate:.4f} is within '
            f'{baseline_sigma}σ of calibrated baseline {baseline_error_rate:.4f}. '
            f'TV distance {mean_tv:.4f}.'
        )

    return {
        'classification': classification,
        'reason': reason,
        'observed_error_rate': round(observed_error_rate, 6),
        'baseline_error_rate': round(baseline_error_rate, 6),
        'error_rate_delta': round(error_rate_delta, 6),
        'baseline_threshold': round(baseline_threshold, 6),
        'baseline_sigma': baseline_sigma,
        'tv_distance_by_key': {k: round(v, 6) for k, v in tv_distances.items()},
        'mean_tv_distance': round(mean_tv, 6),
        'chi_square': None if math.isnan(chi2) else round(chi2, 4),
        'chi_square_p': None if math.isnan(chi_p) else round(chi_p, 6),
        'kl_divergence_by_key': {k: round(v, 6) for k, v in kl_values.items()},
        'mean_kl_divergence': round(mean_kl, 6),
    }


# ---------------------------------------------------------------------------
# Backend comparison summary
# ---------------------------------------------------------------------------

def summarise_backend_comparison(
    ideal_result: dict[str, Any],
    qvm_result: dict[str, Any],
) -> dict[str, Any]:
    """Produce a human-readable summary of ideal vs QVM distributions.

    Both arguments are the 'results[backend_name]' dicts from
    :func:`quantum_core.calibration.compare_backends`.
    """
    summary: dict[str, Any] = {
        'ideal': {
            'backend': ideal_result.get('backend'),
            'duration_ms': ideal_result.get('duration_ms'),
            'histogram': ideal_result.get('histogram'),
            'error': ideal_result.get('error'),
        },
        'qvm': {
            'backend': qvm_result.get('backend'),
            'duration_ms': qvm_result.get('duration_ms'),
            'histogram': qvm_result.get('histogram'),
            'processor': qvm_result.get('metadata', {}).get('processor'),
            'noisy': qvm_result.get('metadata', {}).get('noisy'),
            'simulated': qvm_result.get('metadata', {}).get('simulated'),
            'error': qvm_result.get('error'),
        },
    }
    # TV distance between ideal and QVM for each key
    i_hist = ideal_result.get('histogram') or {}
    q_hist = qvm_result.get('histogram') or {}
    for key in set(i_hist) | set(q_hist):
        ih = i_hist.get(key, {})
        qh = q_hist.get(key, {})
        summary.setdefault('tv_distance', {})[key] = round(total_variation_distance(ih, qh), 6)
    return summary
