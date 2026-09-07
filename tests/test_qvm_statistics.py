"""Tests for QVM-calibrated statistical detection metrics.

All tests use synthetic distributions so they run fast and require no QVM.
The detector mathematics must be correct regardless of which backend generated
the distributions.
"""
import math
import pytest
from detection_engine.statistics import (
    total_variation_distance,
    chi_square_statistic,
    kl_divergence_safe,
    compare_with_baseline,
    summarise_backend_comparison,
)


# ---------------------------------------------------------------------------
# Total variation distance
# ---------------------------------------------------------------------------

class TestTotalVariationDistance:
    def test_identical_distributions_tv_zero(self):
        p = {0: 990, 1: 10}
        assert total_variation_distance(p, p) == pytest.approx(0.0, abs=1e-9)

    def test_fully_separated_distributions_tv_one(self):
        p = {0: 1000}
        q = {1: 1000}
        assert total_variation_distance(p, q) == pytest.approx(1.0, abs=1e-9)

    def test_uniform_vs_uniform_tv_zero(self):
        p = {0: 500, 1: 500}
        q = {0: 500, 1: 500}
        assert total_variation_distance(p, q) == pytest.approx(0.0, abs=1e-9)

    def test_empty_vs_nonempty(self):
        p = {}
        q = {0: 100}
        # Empty hist has total=0 → treated as 0/1 per outcome.
        # q has 100% mass on outcome 0.
        # TV = 0.5 * |0 - 1.0| = 0.5
        assert total_variation_distance(p, q) == pytest.approx(0.5, abs=1e-9)

    def test_tv_is_symmetric(self):
        p = {0: 700, 1: 300}
        q = {0: 500, 1: 500}
        assert total_variation_distance(p, q) == pytest.approx(
            total_variation_distance(q, p), abs=1e-9
        )

    def test_tv_bounded_zero_to_one(self):
        p = {0: 800, 1: 200}
        q = {0: 200, 1: 800}
        tv = total_variation_distance(p, q)
        assert 0.0 <= tv <= 1.0


# ---------------------------------------------------------------------------
# Chi-square statistic
# ---------------------------------------------------------------------------

class TestChiSquare:
    def test_identical_distributions_chi_near_zero(self):
        h = {0: 500, 1: 500}
        chi2, pval = chi_square_statistic(h, h)
        assert not math.isnan(chi2)
        assert chi2 == pytest.approx(0.0, abs=1e-6)

    def test_perfect_mismatch_gives_high_chi(self):
        observed = {0: 0, 1: 1000}
        expected = {0: 1000, 1: 0}
        chi2, pval = chi_square_statistic(observed, expected)
        # With all mass on wrong bin, chi2 should be very large or nan (zero expected)
        # After zero-bin removal only one bin remains — should return nan
        assert math.isnan(chi2) or chi2 > 100

    def test_returns_nan_for_single_bin(self):
        h = {0: 1000}
        chi2, pval = chi_square_statistic(h, h)
        # Only one bin → fewer than 2 bins for chi-square
        assert math.isnan(chi2)


# ---------------------------------------------------------------------------
# KL divergence
# ---------------------------------------------------------------------------

class TestKLDivergence:
    def test_identical_distributions_kl_near_zero(self):
        p = {0: 990, 1: 10}
        kl = kl_divergence_safe(p, p)
        assert kl == pytest.approx(0.0, abs=0.01)

    def test_divergent_distributions_kl_positive(self):
        p = {0: 990, 1: 10}
        q = {0: 10, 1: 990}
        kl = kl_divergence_safe(p, q)
        assert kl > 0.1

    def test_handles_zero_bins(self):
        p = {0: 1000, 1: 0}
        q = {0: 0, 1: 1000}
        kl = kl_divergence_safe(p, q)
        assert math.isfinite(kl)
        assert kl > 0


# ---------------------------------------------------------------------------
# compare_with_baseline — classification correctness
# ---------------------------------------------------------------------------

class TestCompareWithBaseline:
    """Synthetic distributions to verify detector classification logic."""

    BASELINE_HIST = {'m': {0: 990, 1: 10}}       # 1% error rate
    BASELINE_ERR  = 0.01
    THRESHOLD     = 0.025                          # ~0.01 + 3σ
    SIGMA         = 3.0

    def _run(self, observed_hist):
        return compare_with_baseline(
            observed_histogram=observed_hist,
            baseline_histogram=self.BASELINE_HIST,
            baseline_error_rate=self.BASELINE_ERR,
            baseline_threshold=self.THRESHOLD,
            baseline_sigma=self.SIGMA,
            expected_ideal={'m': 0},
        )

    def test_legitimate_distribution_classified_as_legitimate(self):
        # 1% error — within baseline
        obs = {'m': {0: 990, 1: 10}}
        result = self._run(obs)
        assert result['classification'] == 'legitimate'

    def test_strong_attack_classified_as_attack(self):
        # 30% error — well above threshold
        obs = {'m': {0: 700, 1: 300}}
        result = self._run(obs)
        assert result['classification'] == 'attack'

    def test_moderate_deviation_not_legitimate(self):
        # 5% error — above threshold (0.025)
        obs = {'m': {0: 950, 1: 50}}
        result = self._run(obs)
        # Should be suspicious or attack, not legitimate
        assert result['classification'] in ('suspicious', 'attack')

    def test_near_normal_is_not_attack(self):
        # 1.5% error — close to baseline
        obs = {'m': {0: 985, 1: 15}}
        result = self._run(obs)
        assert result['classification'] != 'attack'

    def test_result_contains_required_fields(self):
        obs = {'m': {0: 900, 1: 100}}
        result = self._run(obs)
        required = {
            'classification', 'reason', 'observed_error_rate',
            'baseline_error_rate', 'error_rate_delta', 'baseline_threshold',
            'mean_tv_distance',
        }
        assert required.issubset(set(result.keys()))

    def test_error_rate_delta_positive_for_attack(self):
        obs = {'m': {0: 700, 1: 300}}
        result = self._run(obs)
        assert result['error_rate_delta'] > 0

    def test_error_rate_delta_near_zero_for_legitimate(self):
        obs = {'m': {0: 990, 1: 10}}
        result = self._run(obs)
        assert abs(result['error_rate_delta']) < 0.01

    def test_reason_is_non_empty_string(self):
        obs = {'m': {0: 500, 1: 500}}
        result = self._run(obs)
        assert isinstance(result['reason'], str)
        assert len(result['reason']) > 10

    def test_empty_observed_histogram_returns_error(self):
        result = compare_with_baseline(
            observed_histogram={},
            baseline_histogram=self.BASELINE_HIST,
            baseline_error_rate=self.BASELINE_ERR,
            baseline_threshold=self.THRESHOLD,
            baseline_sigma=self.SIGMA,
        )
        assert result.get('error') is True or result['classification'] == 'unknown'

    def test_full_flip_classified_as_attack(self):
        """All-1 outcomes when ideal is 0 should be detected as attack."""
        obs = {'m': {1: 1000}}
        result = self._run(obs)
        assert result['classification'] == 'attack'
        assert result['observed_error_rate'] == pytest.approx(1.0, abs=0.01)

    def test_tv_distance_zero_for_identical_distributions(self):
        obs = dict(self.BASELINE_HIST)
        result = self._run(obs)
        assert result['mean_tv_distance'] == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Summarise backend comparison
# ---------------------------------------------------------------------------

class TestSummariseBackendComparison:
    def test_returns_ideal_and_qvm_keys(self):
        ideal = {'backend': 'ideal', 'duration_ms': 1.0, 'histogram': {'m': {0: 1000}}, 'error': None}
        qvm = {'backend': 'qvm', 'duration_ms': 50.0, 'histogram': {'m': {0: 980, 1: 20}},
               'metadata': {'processor': 'willow_pink', 'noisy': True, 'simulated': True}, 'error': None}
        summary = summarise_backend_comparison(ideal, qvm)
        assert 'ideal' in summary
        assert 'qvm' in summary

    def test_tv_distance_computed(self):
        ideal = {'backend': 'ideal', 'duration_ms': 1.0, 'histogram': {'m': {0: 1000}}, 'error': None}
        qvm = {'backend': 'qvm', 'duration_ms': 50.0, 'histogram': {'m': {0: 980, 1: 20}},
               'metadata': {'processor': 'willow_pink', 'noisy': True, 'simulated': True}, 'error': None}
        summary = summarise_backend_comparison(ideal, qvm)
        assert 'tv_distance' in summary
        assert 'm' in summary['tv_distance']
        assert 0.0 <= summary['tv_distance']['m'] <= 1.0
