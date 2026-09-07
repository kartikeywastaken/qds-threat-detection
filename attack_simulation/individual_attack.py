"""BB84 intercept-measure-reset-reprepare attack."""
import numpy as np
from qiskit import QuantumCircuit
from attack_simulation.attack_strategy_base import AttackStrategyBase


class IndividualAttackStrategy(AttackStrategyBase):
    """Random X/Z interception; predicts QBER=strength/4 without device noise."""
    def variant(self, rng: np.random.Generator) -> tuple:
        """Choose interception and Eve's basis independently of secret preparation."""
        return (int(rng.random()<self.strength),int(rng.integers(0,2)))

    def apply(self, qc: QuantumCircuit, signal: int, probe: int, classical: int, choice: tuple) -> None:
        """Actually measure, discard the state, and prepare the measured eigenstate."""
        hit,basis=choice
        if not hit: return
        if basis: qc.h(signal)
        qc.measure(signal,classical); qc.reset(signal)
        with qc.if_test((qc.clbits[classical],1)): qc.x(signal)
        if basis: qc.h(signal)
