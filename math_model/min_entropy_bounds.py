"""Bounds for the explicitly restricted independent probe model (§1)."""
import math
from scipy.special import logsumexp, gammaln


def min_entropy_rate(q: float) -> float:
    """Helstrom entropy for equiprobable pure probes of overlap 1-2Q."""
    if not math.isfinite(q) or not 0 <= q <= .5:
        raise ValueError('Q must be finite and in [0, 0.5]')
    return -math.log2(.5 + math.sqrt(q * (1 - q)))


def forgery_bound(n: int, q: float, epsilon: float = 1e-6, tolerated_errors: int = 0) -> float:
    """Union bound on a Hamming ball under the independent probe assumptions."""
    if not isinstance(n, int) or n < 1 or not 0 <= tolerated_errors <= n:
        raise ValueError('Require positive integer n and 0 <= tolerated_errors <= n')
    if not 0 <= epsilon < 1:
        raise ValueError('epsilon must be in [0,1)')
    log_volume = logsumexp([gammaln(n+1)-gammaln(k+1)-gammaln(n-k+1) for k in range(tolerated_errors+1)])
    return min(1., math.exp(min(0., log_volume - n * min_entropy_rate(q) * math.log(2))) + epsilon)


def chsh_entropy(s_lower: float) -> float:
    """Single-round local-output entropy from a valid CHSH lower bound (§2)."""
    if not math.isfinite(s_lower) or not 0 <= s_lower <= 2 * math.sqrt(2) + 1e-10:
        raise ValueError('CHSH lower bound outside quantum domain')
    if s_lower <= 2:
        return 0.
    return 1 - math.log2(1 + math.sqrt(max(0., 2 - s_lower*s_lower/4)))
