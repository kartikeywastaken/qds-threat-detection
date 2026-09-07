"""Authenticated-channel tampering without the sender's key."""
from qds_protocol.measurement_record import SignaturePayload
from attack_simulation.individual_attack import IndividualAttackStrategy


class ChannelManipulationInjector(IndividualAttackStrategy):
    """Combine quantum interception with modified classical message content."""
    def envelope(self, payload: SignaturePayload) -> SignaturePayload:
        """Tampering makes the existing MAC fail by actual cryptographic comparison."""
        return payload.model_copy(update={'message':payload.message+' [modified in transit]'}) if self.strength>0 else payload
