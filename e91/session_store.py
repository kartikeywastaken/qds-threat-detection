"""Bounded, expiring in-memory simulated sessions; no persistence of keys."""
from collections import OrderedDict
from threading import RLock
from time import monotonic
from uuid import uuid4
from .key_exchange import E91Result


class SessionStore:
    def __init__(self, max_sessions=64, ttl_seconds=900, clock=monotonic):
        if max_sessions < 1 or ttl_seconds <= 0:
            raise ValueError('capacity and TTL must be positive')
        self.max_sessions, self.ttl_seconds = max_sessions, ttl_seconds
        self._clock, self._lock = clock, RLock()
        self._sessions = OrderedDict()

    def _purge(self):
        now = self._clock()
        while self._sessions and next(iter(self._sessions.values()))[0] <= now:
            self._sessions.popitem(last=False)

    def add(self, result: E91Result) -> str:
        with self._lock:
            self._purge()
            while len(self._sessions) >= self.max_sessions:
                self._sessions.popitem(last=False)
            session_id = str(uuid4())
            self._sessions[session_id] = (self._clock() + self.ttl_seconds, result)
            return session_id

    def get(self, session_id: str) -> E91Result:
        with self._lock:
            self._purge()
            return self._sessions[session_id][1]

    def key(self, session_id: str, party: str) -> str:
        if party not in ('alice', 'bob'):
            raise KeyError(party)
        result = self.get(session_id)
        key = getattr(result, party + '_key')
        if result.aborted or not key:
            raise KeyError('key unavailable')
        return key

    def latest(self):
        with self._lock:
            self._purge()
            return next(reversed(self._sessions), None)

    def __len__(self):
        with self._lock:
            self._purge()
            return len(self._sessions)
