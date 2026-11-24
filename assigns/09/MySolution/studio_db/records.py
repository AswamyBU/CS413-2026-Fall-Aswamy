"""Immutable record values and their JSON representations.

Records are frozen dataclasses. An update never changes a record in place; it
stores a *new* value. That is what makes list snapshots cheap and exact: a
snapshot just keeps references to the values that existed when it was taken.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def iso(moment: datetime) -> str:
    """UTC ISO 8601 with milliseconds and a Z suffix."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{moment.microsecond // 1000:03d}Z"


@dataclass(frozen=True)
class Expected:
    kind: str                 # "value" | "error"
    value: str | None = None  # for kind == "value"
    category: str | None = None  # "syntax" | "type" for kind == "error"

    def to_json(self) -> dict:
        if self.kind == "value":
            return {"kind": "value", "value": self.value}
        return {"kind": "error", "category": self.category}


@dataclass(frozen=True)
class Case:
    id: str
    name: str
    source: str
    expected: Expected
    description: str

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "source": self.source,
                "expected": self.expected.to_json(), "description": self.description}


@dataclass(frozen=True)
class Program:
    id: str
    name: str
    source: str
    description: str
    created_at: datetime
    updated_at: datetime
    revision: int
    seq: int = field(compare=False)  # creation order, for deterministic listing

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "source": self.source,
                "description": self.description, "created_at": iso(self.created_at),
                "updated_at": iso(self.updated_at), "revision": self.revision}


@dataclass(frozen=True)
class Collection:
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    revision: int
    cases: tuple[Case, ...]
    seq: int = field(compare=False)

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description,
                "created_at": iso(self.created_at), "updated_at": iso(self.updated_at),
                "revision": self.revision, "cases": [c.to_json() for c in self.cases]}
