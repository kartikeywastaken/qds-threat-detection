"""Environment configuration for local experiments, without cloud credentials."""
from dataclasses import dataclass
from pathlib import Path
import math
import os


@dataclass(frozen=True)
class QuantumConfig:
    """Application defaults; legacy library calls remain explicitly available."""
    backend: str = 'qvm'
    shots: int = 2000
    processor: str = 'willow'
    seed: int | None = None
    baseline_required: bool = True
    detection_sigma: float = 3.
    baseline_directory: Path = Path('artifacts/baselines')

    def __post_init__(self) -> None:
        if self.backend not in ('ideal', 'qvm', 'legacy'):
            raise ValueError('DPM_QUANTUM_BACKEND must be ideal, qvm, or legacy')
        if not 16 <= self.shots <= 100000:
            raise ValueError('DPM_QUANTUM_SHOTS must be between 16 and 100000')
        if self.seed is not None and not 0 <= self.seed < 2**32:
            raise ValueError('DPM_QVM_SEED must be an unsigned 32-bit integer')
        if not math.isfinite(self.detection_sigma) or not 1 <= self.detection_sigma <= 8:
            raise ValueError('DPM_DETECTION_SIGMA must be finite in [1,8]')
        if self.processor not in ('willow', 'willow_pink'):
            raise ValueError('This application supports the local willow_pink QVM')

    @classmethod
    def from_env(cls) -> 'QuantumConfig':
        """Read only DPM settings; .env is never implicitly modified or loaded."""
        required = os.getenv('DPM_BASELINE_REQUIRED', 'true').lower()
        if required not in ('true', 'false'):
            raise ValueError('DPM_BASELINE_REQUIRED must be true or false')
        seed = os.getenv('DPM_QVM_SEED', '').strip()
        return cls(backend=os.getenv('DPM_QUANTUM_BACKEND', 'qvm'),
                   shots=int(os.getenv('DPM_QUANTUM_SHOTS', os.getenv('DPM_QVM_SHOTS', '2000'))),
                   processor=os.getenv('DPM_QVM_PROCESSOR', 'willow'),
                   seed=int(seed) if seed else None, baseline_required=required == 'true',
                   detection_sigma=float(os.getenv('DPM_DETECTION_SIGMA', '3')),
                   baseline_directory=Path(os.getenv('DPM_BASELINE_DIRECTORY', 'artifacts/baselines')))
