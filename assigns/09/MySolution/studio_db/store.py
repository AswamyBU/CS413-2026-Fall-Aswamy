"""Storage interface and the required in-memory backend.

The service talks to storage only through `Store`. Another backend could be
dropped in by implementing these five methods; the required backend keeps
everything in ordinary Python dicts inside the process. Nothing is written to
disk, so all data is lost when the process stops.

The store does no locking and no business checks. The service holds one lock
around each check-and-write sequence, which is what makes mutations atomic.
"""

from __future__ import annotations

from typing import Protocol

PROGRAMS = "programs"
COLLECTIONS = "collections"
KINDS = (PROGRAMS, COLLECTIONS)


class Store(Protocol):
    def get(self, kind: str, record_id: str): ...
    def put(self, kind: str, record) -> None: ...
    def delete(self, kind: str, record_id: str) -> None: ...
    def all(self, kind: str) -> list: ...
    def count(self, kind: str) -> int: ...


class MemoryStore:
    """Records keyed by id, one dict per kind. Values are immutable records."""

    def __init__(self):
        self._tables: dict[str, dict[str, object]] = {kind: {} for kind in KINDS}

    def get(self, kind: str, record_id: str):
        return self._tables[kind].get(record_id)

    def put(self, kind: str, record) -> None:
        self._tables[kind][record.id] = record

    def delete(self, kind: str, record_id: str) -> None:
        del self._tables[kind][record_id]

    def all(self, kind: str) -> list:
        """All records of one kind in creation order (deterministic)."""
        return sorted(self._tables[kind].values(), key=lambda r: r.seq)

    def count(self, kind: str) -> int:
        return len(self._tables[kind])
