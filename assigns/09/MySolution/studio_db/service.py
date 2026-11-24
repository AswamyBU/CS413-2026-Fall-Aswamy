"""Business rules: uniqueness, revisions, preconditions, capacity, atomicity.

No HTTP here. Each operation:
  * takes route values, the raw If-Match header (or None), and a `body`
    thunk that returns decoded JSON or raises the 415/400 it deferred;
  * runs every check and the write while holding one lock, in the order
    documented in API.md section 4, so a request is all-or-nothing;
  * returns an immutable record (or None for a delete).
"""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone

from . import validation
from .config import Limits
from .errors import (CAPACITY_LIMIT, DUPLICATE_NAME, PRECONDITION_REQUIRED,
                     REVISION_CONFLICT, ApiError, not_found)
from .pagination import SnapshotTable
from .records import Case, Collection, Program
from .store import COLLECTIONS, PROGRAMS, MemoryStore, Store

Body = Callable[[], object]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudioService:
    def __init__(self, store: Store | None = None, limits: Limits | None = None, *,
                 clock: Callable[[], datetime] = _utc_now,
                 snapshots: SnapshotTable | None = None):
        self.store = store if store is not None else MemoryStore()
        self.limits = limits or Limits()
        self.clock = clock
        # `is not None`, not `or`: an empty SnapshotTable has len 0 and is falsy.
        self.snapshots = snapshots if snapshots is not None else SnapshotTable(
            max_snapshots=self.limits.max_snapshots,
            idle_seconds=self.limits.snapshot_idle_seconds)
        self._lock = threading.RLock()
        self._seq = 0

    # ------------------------------------------------------------ helpers

    def _now(self) -> datetime:
        return self.clock()

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _new_id(self, prefix: str, taken: Callable[[str], bool]) -> str:
        while True:
            candidate = f"{prefix}_{secrets.token_hex(8)}"
            if not taken(candidate):
                return candidate

    def _require(self, kind: str, record_id: str, label: str):
        record = self.store.get(kind, record_id)
        if record is None:
            raise not_found(f"{label} {record_id} not found")
        return record

    @staticmethod
    def _precondition(if_match: str | None) -> int:
        if if_match is None:
            raise ApiError(428, PRECONDITION_REQUIRED,
                           'If-Match is required; send the ETag from your last read, e.g. "3"')
        return validation.parse_if_match(if_match)

    @staticmethod
    def _check_revision(record, expected: int) -> None:
        if expected != record.revision:
            raise ApiError(409, REVISION_CONFLICT,
                           f'If-Match "{expected}" does not match the current revision '
                           f"{record.revision}", current_revision=record.revision)

    @staticmethod
    def _check_unique(name: str, others, what: str, exclude: str | None = None) -> None:
        for other in others:
            if other.name == name and other.id != exclude:
                raise ApiError(409, DUPLICATE_NAME, f"a {what} named {name!r} already exists",
                               field="name")

    def _check_capacity(self, count: int, limit: int, what: str) -> None:
        if count >= limit:
            raise ApiError(409, CAPACITY_LIMIT, f"capacity limit reached: at most {limit} {what}",
                           limit=limit)

    # ------------------------------------------------------------ listing

    def list_page(self, kind: str, limit: int, cursor: str | None) -> tuple[list, str | None]:
        def capture():
            with self._lock:  # a consistent view of the live records
                return tuple(self.store.all(kind))
        return self.snapshots.page(kind, limit, cursor, capture)

    # ------------------------------------------------------------ programs

    def create_program(self, body: Body) -> Program:
        fields = validation.program_fields(body(), self.limits)
        with self._lock:
            self._check_unique(fields.name, self.store.all(PROGRAMS), "program")
            self._check_capacity(self.store.count(PROGRAMS), self.limits.max_programs, "programs")
            now = self._now()
            program = Program(
                id=self._new_id("prg", lambda i: self.store.get(PROGRAMS, i) is not None),
                name=fields.name, source=fields.source, description=fields.description,
                created_at=now, updated_at=now, revision=1, seq=self._next_seq())
            self.store.put(PROGRAMS, program)
            return program

    def get_program(self, program_id: str) -> Program:
        with self._lock:
            return self._require(PROGRAMS, program_id, "program")

    def update_program(self, program_id: str, if_match: str | None, body: Body) -> Program:
        with self._lock:
            current = self._require(PROGRAMS, program_id, "program")
            expected = self._precondition(if_match)
            fields = validation.program_fields(body(), self.limits)
            self._check_revision(current, expected)
            self._check_unique(fields.name, self.store.all(PROGRAMS), "program", exclude=program_id)
            updated = replace(current, name=fields.name, source=fields.source,
                              description=fields.description, updated_at=self._now(),
                              revision=current.revision + 1)
            self.store.put(PROGRAMS, updated)
            return updated

    def delete_program(self, program_id: str, if_match: str | None) -> None:
        with self._lock:
            current = self._require(PROGRAMS, program_id, "program")
            self._check_revision(current, self._precondition(if_match))
            self.store.delete(PROGRAMS, program_id)
            # Test cases hold their own source snapshots; nothing else changes.

    # ------------------------------------------------------------ collections

    def create_collection(self, body: Body) -> Collection:
        fields = validation.collection_fields(body(), self.limits)
        with self._lock:
            self._check_unique(fields.name, self.store.all(COLLECTIONS), "collection")
            self._check_capacity(self.store.count(COLLECTIONS), self.limits.max_collections,
                                 "collections")
            now = self._now()
            collection = Collection(
                id=self._new_id("col", lambda i: self.store.get(COLLECTIONS, i) is not None),
                name=fields.name, description=fields.description, created_at=now,
                updated_at=now, revision=1, cases=(), seq=self._next_seq())
            self.store.put(COLLECTIONS, collection)
            return collection

    def get_collection(self, collection_id: str) -> Collection:
        with self._lock:
            return self._require(COLLECTIONS, collection_id, "collection")

    def update_collection(self, collection_id: str, if_match: str | None, body: Body) -> Collection:
        with self._lock:
            current = self._require(COLLECTIONS, collection_id, "collection")
            expected = self._precondition(if_match)
            fields = validation.collection_fields(body(), self.limits)
            self._check_revision(current, expected)
            self._check_unique(fields.name, self.store.all(COLLECTIONS), "collection",
                               exclude=collection_id)
            return self._save_collection(current, name=fields.name,
                                         description=fields.description)

    def delete_collection(self, collection_id: str, if_match: str | None) -> None:
        with self._lock:
            current = self._require(COLLECTIONS, collection_id, "collection")
            self._check_revision(current, self._precondition(if_match))
            self.store.delete(COLLECTIONS, collection_id)  # its cases go with it

    def _save_collection(self, current: Collection, **changes) -> Collection:
        updated = replace(current, updated_at=self._now(), revision=current.revision + 1,
                          **changes)
        self.store.put(COLLECTIONS, updated)
        return updated

    # ------------------------------------------------------------ cases

    @staticmethod
    def _case_index(collection: Collection, case_id: str) -> int:
        for index, case in enumerate(collection.cases):
            if case.id == case_id:
                return index
        raise not_found(f"case {case_id} not found in collection {collection.id}")

    def add_case(self, collection_id: str, if_match: str | None, body: Body) -> Collection:
        with self._lock:
            current = self._require(COLLECTIONS, collection_id, "collection")
            expected = self._precondition(if_match)
            fields = validation.case_fields(body(), self.limits)
            self._check_revision(current, expected)
            self._check_unique(fields.name, current.cases, "case in this collection")
            self._check_capacity(len(current.cases), self.limits.max_cases_per_collection,
                                 "cases per collection")
            taken = {c.id for c in current.cases}
            case = Case(id=self._new_id("case", taken.__contains__), name=fields.name,
                        source=fields.source, expected=fields.expected,
                        description=fields.description)
            return self._save_collection(current, cases=current.cases + (case,))

    def update_case(self, collection_id: str, case_id: str, if_match: str | None,
                    body: Body) -> Collection:
        with self._lock:
            current = self._require(COLLECTIONS, collection_id, "collection")
            index = self._case_index(current, case_id)
            expected = self._precondition(if_match)
            fields = validation.case_fields(body(), self.limits)
            self._check_revision(current, expected)
            self._check_unique(fields.name, current.cases, "case in this collection",
                               exclude=case_id)
            case = Case(id=case_id, name=fields.name, source=fields.source,
                        expected=fields.expected, description=fields.description)
            cases = current.cases[:index] + (case,) + current.cases[index + 1:]
            return self._save_collection(current, cases=cases)

    def delete_case(self, collection_id: str, case_id: str, if_match: str | None) -> Collection:
        with self._lock:
            current = self._require(COLLECTIONS, collection_id, "collection")
            index = self._case_index(current, case_id)
            self._check_revision(current, self._precondition(if_match))
            cases = current.cases[:index] + current.cases[index + 1:]
            return self._save_collection(current, cases=cases)
