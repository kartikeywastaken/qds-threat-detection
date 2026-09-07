"""Append-only JSONL events with a verifiable SHA-256 hash chain."""
import fcntl
import hashlib
import json
from pathlib import Path


def digest(event: dict) -> str:
    """Canonical event digest; simulation values remain reproducible."""
    return hashlib.sha256(json.dumps(event,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class SecurityEventLog:
    """Local file writer serialized with OS locks; no secrets are logged."""
    def __init__(self, path: str | Path) -> None:
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)

    def append(self, report: dict) -> dict:
        """Append and fsync one event; reject any existing broken chain."""
        import os
        with self.path.open('a+') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX);handle.seek(0)
            previous='0'*64;sequence=0
            for line in handle:
                item=json.loads(line);stored=item.pop('hash')
                if item['sequence']!=sequence or item['previous']!=previous or digest(item)!=stored: raise ValueError('Event log hash chain corrupted')
                previous=stored;sequence+=1
            event={'sequence':sequence,'previous':previous,'report':report};event['hash']=digest(event)
            handle.write(json.dumps(event,sort_keys=True,allow_nan=False)+'\n');handle.flush();os.fsync(handle.fileno())
            return event

    def read(self) -> list[dict]:
        """Read a consistent snapshot and validate the complete hash chain."""
        if not self.path.exists(): return []
        with self.path.open() as handle:
            fcntl.flock(handle,fcntl.LOCK_SH)
            events=[json.loads(line) for line in handle]
        previous='0'*64
        for i,event in enumerate(events):
            content={k:v for k,v in event.items() if k!='hash'}
            if event['sequence']!=i or event['previous']!=previous or event['hash']!=digest(content): raise ValueError('Event log hash chain corrupted')
            previous=event['hash']
        return events
