"""Bounded live telemetry using the existing hash-chain writer, unchanged."""
from pathlib import Path
from threading import RLock
import os
from presentation.security_event_log import SecurityEventLog


class BoundedEventLog:
    """Keep two 100-event segments; each segment has its own verified chain."""
    def __init__(self, path: Path, max_events: int = 100, max_bytes: int = 256000) -> None:
        self.path = Path(path); self.archive = self.path.with_suffix('.jsonl.1')
        self.max_events = max_events; self.max_bytes = max_bytes; self.lock = RLock()
        self.writer = SecurityEventLog(self.path)
        self.count = len(self.writer.read())

    def append(self, report: dict) -> dict:
        with self.lock:
            if self.count >= self.max_events or (self.path.exists() and self.path.stat().st_size >= self.max_bytes):
                os.replace(self.path, self.archive)
                self.count = 0
            result = self.writer.append(report); self.count += 1
            return result

    def read(self) -> list[dict]:
        with self.lock:
            previous = SecurityEventLog(self.archive).read() if self.archive.exists() else []
            return (previous + self.writer.read())[-2*self.max_events:]
