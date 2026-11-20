"""Process-local table of open event streams (no HTTP, no JSON-RPC here).

Lifecycle of an entry:
  open   -> a fresh EventStream; nothing forced yet.
  next   -> forces at most `limit` cells under the entry's lock.
  done   -> when the `done` event is returned the solver state (lazy stream
            and all its continuation closures) is released at once; a small
            "exhausted" record stays so later `next` calls can answer
            `{"events": [], "done": true}` as the contract requires.
  close  -> entry removed; the id is unknown from then on.
  expire -> entries idle longer than `ttl_seconds` are removed by a sweep
            that runs at the start of every table operation.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from .errors import STREAM_NOT_FOUND, TOO_MANY_STREAMS, RpcError
from .solver import SOLUTION, Backend, EventStream, event_to_json

DEFAULT_TTL_SECONDS = 300.0
DEFAULT_MAX_STREAMS = 64


@dataclass
class _Entry:
    stream: EventStream | None
    size: int
    last_used: float
    lock: threading.Lock = field(default_factory=threading.Lock)
    events_sent: int = 0
    solutions_sent: int = 0
    closed: bool = False

    @property
    def exhausted(self) -> bool:
        return self.stream is None


class StreamTable:
    def __init__(self, backend: Backend, *, ttl_seconds: float = DEFAULT_TTL_SECONDS,
                 max_streams: int = DEFAULT_MAX_STREAMS,
                 clock: Callable[[], float] = time.monotonic):
        self.backend = backend
        self.ttl_seconds = ttl_seconds
        self.max_streams = max_streams
        self.clock = clock
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __contains__(self, stream_id: str) -> bool:
        with self._lock:
            return stream_id in self._entries

    def is_exhausted(self, stream_id: str) -> bool:
        with self._lock:
            return self._entries[stream_id].exhausted

    def sweep(self) -> int:
        """Remove idle entries; return how many were removed."""
        with self._lock:
            return self._sweep_locked()

    def _sweep_locked(self) -> int:
        cutoff = self.clock() - self.ttl_seconds
        stale = [sid for sid, entry in self._entries.items()
                 if entry.last_used < cutoff and not entry.lock.locked()]
        for sid in stale:
            del self._entries[sid]
        return len(stale)

    def open(self, size: int) -> str:
        with self._lock:
            self._sweep_locked()
            if len(self._entries) >= self.max_streams:
                raise RpcError(TOO_MANY_STREAMS, data={"max_streams": self.max_streams})
            stream_id = str(uuid.uuid4())
            # EventStream construction builds the suspended stream only.
            self._entries[stream_id] = _Entry(EventStream(self.backend, size), size,
                                              self.clock())
            return stream_id

    @staticmethod
    def _not_found(stream_id: str) -> RpcError:
        return RpcError(STREAM_NOT_FOUND, "Stream not found (unknown, closed, or expired)",
                        {"stream_id": stream_id[:64]})

    def _lookup(self, stream_id: str) -> _Entry:
        with self._lock:
            self._sweep_locked()
            entry = self._entries.get(stream_id)
            if entry is None:
                raise self._not_found(stream_id)
            entry.last_used = self.clock()
            return entry

    def next(self, stream_id: str, limit: int) -> dict:
        entry = self._lookup(stream_id)
        with entry.lock:  # one request advances a stream at a time
            if entry.closed:  # closed by a concurrent request
                raise self._not_found(stream_id)
            if entry.exhausted:
                return {"events": [], "done": True}
            events = []
            for event in entry.stream.take(limit):
                encoded = event_to_json(event)
                encoded["seq"] = entry.events_sent
                entry.events_sent += 1
                if event.kind == SOLUTION:
                    entry.solutions_sent += 1
                    encoded["number"] = entry.solutions_sent
                events.append(encoded)
            if entry.stream.finished:
                entry.stream = None  # release solver state; keep the record
            entry.last_used = self.clock()
            return {"events": events, "done": entry.exhausted}

    def close(self, stream_id: str) -> dict:
        entry = self._lookup(stream_id)
        with self._lock:
            if self._entries.get(stream_id) is entry:
                del self._entries[stream_id]
        with entry.lock:  # wait for any in-flight `next` on this stream
            entry.closed = True
            entry.stream = None
        return {"closed": True}
