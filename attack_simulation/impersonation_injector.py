"""Classical sender substitution and entanglement-breaking resource substitution."""
import numpy as np
from qiskit import QuantumCircuit
from qds_protocol.measurement_record import SignaturePayload
from attack_simulation.individual_attack import IndividualAttackStrategy


class ImpersonationInjector(IndividualAttackStrategy):
    """Unsigned identity substitution plus randomly intercepted quantum traffic."""
    def envelope(self, payload: SignaturePayload) -> SignaturePayload:
        """Change sender without possession of the legitimate authentication key."""
        return payload.model_copy(update={'sender':'mallory'}) if self.strength>0 else payload

    def resource(self, qc: QuantumCircuit, rng: np.random.Generator) -> bool:
        """On selected pairs, dephase Alice by actual measurement in Z."""
        replaced=bool(rng.random()<self.strength)
        if replaced: qc.measure(0,2)
        return replaced
