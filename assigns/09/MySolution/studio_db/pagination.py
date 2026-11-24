"""Snapshot cursors for list routes (API.md section 6).

The first page of a listing captures a tuple of the current immutable
records. Each `next_cursor` is a random token mapped to (snapshot, offset),
so every later page in that chain reads the same captured values in the same
order, whatever happens to the live records meanwhile.

Snapshots live only in this process: they expire after an idle period, the
least recently used is evicted beyond a fixed count, and all of them vanish
when the process stops.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

from .errors import invalid


@dataclass
class _Snapshot:
    kind: str
    items: tuple
    last_used: float
    tokens: list[str] = field(default_factory=list)


class SnapshotTable:
    def __init__(self, *, max_snapshots: int, idle_seconds: float,
                 clock: Callable[[], float] = time.monotonic):
        self.max_snapshots = max_snapshots
        self.idle_seconds = idle_seconds
        self.clock = clock
        self._snapshots: OrderedDict[int, _Snapshot] = OrderedDict()
        self._cursors: dict[str, tuple[int, int]] = {}  # token -> (snapshot id, offset)
        self._next_id = 0
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def page(self, kind: str, limit: int, cursor: str | None,
             capture: Callable[[], tuple]) -> tuple[list, str | None]:
        """Return (records, next_cursor). `capture` is called only for a first page."""
        with self._lock:
            now = self.clock()
            self._expire(now)
            if cursor is None:
                snapshot_id = self._next_id
                self._next_id += 1
                self._snapshots[snapshot_id] = _Snapshot(kind, capture(), now)
                offset = 0
                while len(self._snapshots) > self.max_snapshots:
                    self._drop(next(iter(self._snapshots)))
            else:
                location = self._cursors.get(cursor)
                if location is None or self._snapshots[location[0]].kind != kind:
                    raise invalid("cursor is invalid or expired; start again without a cursor",
                                  parameter="cursor")
                snapshot_id, offset = location
            snapshot = self._snapshots[snapshot_id]
            snapshot.last_used = now
            self._snapshots.move_to_end(snapshot_id)
            items = list(snapshot.items[offset:offset + limit])
            next_cursor = None
            if offset + limit < len(snapshot.items):
                next_cursor = secrets.token_urlsafe(16)
                self._cursors[next_cursor] = (snapshot_id, offset + limit)
                snapshot.tokens.append(next_cursor)
            return items, next_cursor

    def _expire(self, now: float) -> None:
        stale = [sid for sid, s in self._snapshots.items()
                 if now - s.last_used > self.idle_seconds]
        for sid in stale:
            self._drop(sid)

    def _drop(self, snapshot_id: int) -> None:
        snapshot = self._snapshots.pop(snapshot_id)
        for token in snapshot.tokens:
            self._cursors.pop(token, None)
