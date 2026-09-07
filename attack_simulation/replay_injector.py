"""Capture and resubmit a genuine previously consumed envelope."""
from qds_protocol.measurement_record import SignaturePayload


class ReplayInjector:
    """Replay has no need to counterfeit the MAC or quantum state."""
    def __init__(self) -> None:
        self.captured: SignaturePayload | None=None

    def capture(self, payload: SignaturePayload) -> None:
        """Store a wire payload unchanged."""
        self.captured=payload.model_copy()

    def inject(self) -> SignaturePayload:
        """Return captured bytes-equivalent payload."""
        if self.captured is None: raise ValueError('No captured payload to replay')
        return self.captured.model_copy()
