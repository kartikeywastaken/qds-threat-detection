"""Strategy interface and honest identity channel."""
import math
import numpy as np
from qiskit import QuantumCircuit
from qds_protocol.measurement_record import Distribution, MeasurementRecord
from qds_protocol.teleportation_engine import transmit


class AttackStrategyBase:
    """Executable honest channel; subclasses replace physical circuit interaction."""
    def __init__(self, strength: float=0.) -> None:
        if not math.isfinite(strength) or not 0 <= strength <= 1: raise ValueError('Strength must be in [0,1]')
        self.strength=strength

    def variant(self, rng: np.random.Generator) -> tuple:
        """Identity channel has no random branch."""
        return ()

    def apply(self, qc: QuantumCircuit, signal: int, probe: int, classical: int, choice: tuple) -> None:
        """Identity gate implements the no-attack control."""
        qc.id(signal)

    def transmit(self, distribution: Distribution, exposure: float, seed: int) -> list[MeasurementRecord]:
        """Send quantum states through the strategy and actual teleportation."""
        return transmit(distribution,exposure,seed,self.apply,self.variant)
