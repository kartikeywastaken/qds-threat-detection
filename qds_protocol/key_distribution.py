"""Seeded BB84 preparation schedule and session setup."""
import numpy as np
from qds_protocol.measurement_record import Distribution


def distribute(n: int, seed: int) -> Distribution:
    """Generate uniform secret bits/bases; circuits are sent during signing."""
    if not isinstance(n,int) or not 1 <= n <= 100000 or seed < 0:
        raise ValueError('Require 1<=n<=100000 and nonnegative seed')
    rng=np.random.default_rng(seed)
    return Distribution(session_id=rng.bytes(16).hex(),bits=tuple(map(int,rng.integers(0,2,n))),
                        bases=tuple('X' if x else 'Z' for x in rng.integers(0,2,n)),auth_key=rng.bytes(32))
