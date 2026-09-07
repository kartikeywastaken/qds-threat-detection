"""Cached local backend selection; Engine is deliberately unavailable."""
from functools import lru_cache
from quantum_core.base import QuantumBackend
from quantum_core.config import QuantumConfig
from quantum_core.errors import UnknownQuantumBackend


@lru_cache(maxsize=16)
def _backend(name: str, seed: int | None, processor: str) -> QuantumBackend:
    if name == 'ideal':
        from quantum_core.ideal import IdealCirqBackend
        return IdealCirqBackend(seed)
    if name == 'qvm':
        from quantum_core.qvm import GoogleQVMBackend
        return GoogleQVMBackend(processor=processor, seed=seed)
    if name == 'engine':
        raise UnknownQuantumBackend('Engine is reserved; physical hardware execution is not implemented')
    raise UnknownQuantumBackend(f'Unknown circuit backend {name!r}; use ideal or qvm')


def get_quantum_backend(name: str | None = None, *, seed: int | None = None,
                        processor: str | None = None) -> QuantumBackend:
    """Return a lazy, reusable backend; never substitute ideal for a failed QVM."""
    config = QuantumConfig.from_env()
    return _backend(name or config.backend, config.seed if seed is None else seed,
                    processor or config.processor)
