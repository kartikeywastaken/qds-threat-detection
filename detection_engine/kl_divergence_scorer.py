"""Natural-log KL divergence with explicit support checks."""
import numpy as np
from scipy.stats import entropy


def kl_divergence(p: np.ndarray, reference: np.ndarray) -> float:
    """Compute D_KL(P||R) in nats; reject invalid probability vectors."""
    p=np.asarray(p,dtype=float);reference=np.asarray(reference,dtype=float)
    if p.ndim!=1 or p.shape!=reference.shape or not len(p): raise ValueError('Distribution shapes differ')
    for x in (p,reference):
        if not np.isfinite(x).all() or (x<0).any() or not np.isclose(x.sum(),1): raise ValueError('Invalid probability distribution')
    if ((p>0)&(reference==0)).any(): raise ValueError('Reference assigns zero probability to observed support')
    return float(entropy(p,reference))
