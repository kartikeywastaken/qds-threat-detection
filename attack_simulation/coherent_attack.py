"""Reduced coherent attack: noncommuting interactions through a shared probe."""
import numpy as np
from qiskit import QuantumCircuit
from attack_simulation.collective_attack import CollectiveAttackStrategy


class CoherentAttackStrategy(CollectiveAttackStrategy):
    """Shared quantum memory entangles two signals; not an independent channel."""
    def interact(self, qc: QuantumCircuit) -> None:
        """A common probe mediates joint signal interaction before deferred readout."""
        qc.cry(np.pi*self.strength,0,2)
        qc.h(2); qc.crz(np.pi*self.strength,1,2); qc.h(2)
        qc.cry(np.pi*self.strength,2,1)
