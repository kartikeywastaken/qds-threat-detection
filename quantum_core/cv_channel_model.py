"""Continuous-variable Gaussian loss computed by Strawberry Fields."""
import math
import numpy as np
import strawberryfields as sf
from strawberryfields import ops


def simulate_cv(transmissivity: float = .8, thermal_photons: float = .05, squeezing: float = .5) -> dict:
    """Two-mode squeezed resource through a thermal loss channel; exact moments."""
    if not all(math.isfinite(x) for x in (transmissivity, thermal_photons, squeezing)):
        raise ValueError('CV parameters must be finite')
    if not 0 <= transmissivity <= 1 or thermal_photons < 0 or not 0 <= squeezing <= 3:
        raise ValueError('Invalid CV channel parameter')
    program = sf.Program(2)
    with program.context as q:
        ops.S2gate(squeezing) | (q[0],q[1])
        ops.ThermalLossChannel(transmissivity, thermal_photons) | q[1]
    state = sf.Engine('gaussian').run(program).state
    covariance = state.cov()
    if not np.allclose(covariance,covariance.T) or np.linalg.eigvalsh(covariance).min() <= 0:
        raise ArithmeticError('Invalid Gaussian covariance')
    return {'hbar':float(sf.hbar), 'means':state.means().tolist(), 'covariance':covariance.tolist(),
            'mean_photons':[float(state.mean_photon(i)[0]) for i in range(2)]}
