"""Canonical, domain-separated wallet envelope, shared by both gateways."""
import json
from pydantic import BaseModel, ConfigDict, Field


class Envelope(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    transfer_id: str = Field(min_length=1, max_length=64)
    from_user: str = Field(min_length=1, max_length=100)
    to_user: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(gt=0, le=9007199254740991)
    nonce: str = Field(min_length=16, max_length=128)


def canonical(envelope: Envelope | dict) -> bytes:
    parsed = envelope if isinstance(envelope, Envelope) else Envelope.model_validate(envelope)
    return json.dumps({'_domain': 'QDS-WALLET-v1', **parsed.model_dump()},
                      sort_keys=True, separators=(',', ':')).encode()
