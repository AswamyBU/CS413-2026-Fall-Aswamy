"""Backend contract: operations, result statuses, artifacts, and the
LanguageBackend protocol.

Shared by the model (which stores results), the controller (which dispatches
operations), and any backend implementation.  It contains data types only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class Operation(str, Enum):
    LINT = "lint"
    INTERPRET = "interpret"
    TYPECHECK = "typecheck"
    COMPILE = "compile"
    EXECUTE = "execute"


class Status(str, Enum):
    OK = "ok"                            # operation succeeded
    INPUT_ERROR = "input_error"          # source is not a valid d0exp
    LANGUAGE_ERROR = "language_error"    # valid input, but the program is wrong
                                         # (free variables, runtime failure)
    BACKEND_FAILURE = "backend_failure"  # the tool itself failed or timed out
    NOT_IMPLEMENTED = "not_implemented"  # placeholder operation
    UNAVAILABLE = "unavailable"          # preconditions not met (e.g. no artifact)


@dataclass(frozen=True)
class Artifact:
    """Generated code produced by Compile and consumed by Execute.

    Contract for a future compiler: ``revision`` is the source revision it was
    compiled from; ``target`` names the format (e.g. "python", "js");
    ``code`` is the generated program text.  Execute must refuse an artifact
    whose revision is not the model's current revision.
    """
    revision: int
    target: str
    code: str


@dataclass(frozen=True)
class OpResult:
    operation: Operation
    revision: int
    status: Status
    summary: str                 # one-line headline
    output: str = ""             # full textual output / diagnostic
    artifact: Artifact | None = field(default=None, compare=False)

    @property
    def ok(self) -> bool:
        return self.status is Status.OK


class LanguageBackend(Protocol):
    def lint(self, source: str, revision: int) -> OpResult: ...
    def interpret(self, source: str, revision: int) -> OpResult: ...
    def typecheck(self, source: str, revision: int) -> OpResult: ...
    def compile(self, source: str, revision: int) -> OpResult: ...
    def execute(self, artifact: Artifact | None, revision: int) -> OpResult: ...
