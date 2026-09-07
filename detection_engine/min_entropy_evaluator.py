"""Explicitly scoped entropy evaluations, without overclaiming QDS security."""
from math_model.min_entropy_bounds import chsh_entropy, forgery_bound


def evaluate(chsh: dict, n: int, q_model: float=.04, epsilon: float=1e-6) -> dict:
    """Return single-round witness plus a separately labeled hypothetical iid bound."""
    return {'chsh_bits_per_round_lower':chsh_entropy(chsh['lower']),
            'restricted_iid_forgery_bound':forgery_bound(n,q_model,epsilon),
            'q_model':q_model,'epsilon':epsilon,
            'scope':'Pure independent probes with overlap 1-2Q only; not a general QDS certificate'}
