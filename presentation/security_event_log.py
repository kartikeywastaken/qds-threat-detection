import fcntl
import hashlib
import json
import logging
from pathlib import Path

# Try to initialize Firebase
import firebase_admin
from firebase_admin import credentials, firestore

firebase_db = None
cred_path = Path('firebase-credentials.json')
if cred_path.exists():
    try:
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
        firebase_db = firestore.client()
        logging.info("Firebase initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Firebase: {e}")
else:
    logging.warning("firebase-credentials.json not found. Falling back to local logging.")

def digest(event: dict) -> str:
    """Canonical event digest; simulation values remain reproducible."""
    return hashlib.sha256(json.dumps(event,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class SecurityEventLog:
    """Local file writer serialized with OS locks; no secrets are logged. Also pushes to Firebase if configured."""
    def __init__(self, path: str | Path) -> None:
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)

    def append(self, report: dict) -> dict:
        """Append and fsync one event; reject any existing broken chain. Pushes to Firebase."""
        import os
        with self.path.open('a+') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX);handle.seek(0)
            previous='0'*64;sequence=0
            for line in handle:
                if not line.strip(): continue
                item=json.loads(line);stored=item.pop('hash', None)
                if stored and (item['sequence']!=sequence or item['previous']!=previous or digest(item)!=stored): 
                    raise ValueError('Event log hash chain corrupted')
                previous=stored if stored else '0'*64
                sequence+=1
            event={'sequence':sequence,'previous':previous,'report':report};event['hash']=digest(event)
            handle.write(json.dumps(event,sort_keys=True,allow_nan=False)+'\n');handle.flush();os.fsync(handle.fileno())
            
        # Push to Firebase asynchronously or safely
        if firebase_db:
            try:
                firebase_db.collection('qds_events').document(str(sequence)).set(event)
            except Exception as e:
                logging.error(f"Firebase write failed: {e}")
                
        return event

    def read(self) -> list[dict]:
        """Read a consistent snapshot and validate the complete hash chain."""
        # If Firebase is active, we could read from there, but for speed we read local cache
        if not self.path.exists(): return []
        with self.path.open() as handle:
            fcntl.flock(handle,fcntl.LOCK_SH)
            events=[json.loads(line) for line in handle if line.strip()]
        previous='0'*64
        for i,event in enumerate(events):
            content={k:v for k,v in event.items() if k!='hash'}
            if event['sequence']!=i or event['previous']!=previous or event['hash']!=digest(content): raise ValueError('Event log hash chain corrupted')
            previous=event['hash']
        return events

