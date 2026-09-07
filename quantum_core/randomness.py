"""Domain-separated deterministic seeds for independent simulator streams."""
import hashlib


def simulator_seed(root: int, stream: int=0) -> int:
    """Mix adjacent user seeds before seeding Aer; do not reuse shot RNG streams."""
    if not isinstance(root,int) or not isinstance(stream,int) or root<0 or stream<0:
        raise ValueError('Seed and stream must be nonnegative integers')
    encoded=f'qds-aer-v1:{root}:{stream}'.encode()
    return int.from_bytes(hashlib.sha256(encoded).digest()[:4],'big')
