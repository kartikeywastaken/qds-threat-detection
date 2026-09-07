"""Validated observations shared by protocol, detection, and presentation."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal


class MeasurementRecord(BaseModel):
    """A receiver-owned measured round; never contains a scenario label."""
    model_config = ConfigDict(extra='forbid', frozen=True)
    index: int = Field(ge=0)
    expected: Literal[0,1]
    observed: Literal[0,1]
    basis: Literal['X','Z']
    bell_bits: tuple[Literal[0,1],Literal[0,1]]

    @property
    def error(self) -> int:
        """Bernoulli observation in security model §3."""
        return int(self.expected != self.observed)


class SignaturePayload(BaseModel):
    """Classical envelope referring to a privately stored quantum receipt."""
    model_config = ConfigDict(extra='forbid', frozen=True)
    session_id: str = Field(min_length=1,max_length=128)
    sender: str = Field(min_length=1,max_length=128)
    nonce: str = Field(min_length=1,max_length=128)
    message: str = Field(min_length=1,max_length=10000)
    tag: str = Field(pattern=r'^[0-9a-f]{64}$')


class Distribution(BaseModel):
    """Verifier's private preparation data, generated for one signing session."""
    model_config = ConfigDict(extra='forbid', frozen=True)
    session_id: str
    bits: tuple[Literal[0,1],...]
    bases: tuple[Literal['X','Z'],...]
    auth_key: bytes

    @model_validator(mode='after')
    def validate_lengths(self) -> 'Distribution':
        """Reject malformed or empty preparation schedules."""
        if not self.bits or len(self.bits)!=len(self.bases) or len(self.auth_key)!=32:
            raise ValueError('Distribution lengths or authentication key invalid')
        return self
