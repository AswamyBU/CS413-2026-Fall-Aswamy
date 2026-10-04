"""Workbench model: the application state and the rules that govern it.

This module is pure Python.  It knows nothing about Flask, HTTP requests,
HTML, or how language tools are invoked; it stores ``OpResult`` values the
controller hands it and decides which actions are currently allowed.
"""

from __future__ import annotations

from dataclasses import dataclass

from contract import Artifact, OpResult, Operation, Status

MAX_SOURCE_BYTES = 64 * 1024   # documented limit on uploaded/applied source

ACTION_ORDER = [Operation.LINT, Operation.INTERPRET, Operation.TYPECHECK,
                Operation.COMPILE, Operation.EXECUTE]
ACTION_LABELS = {
    Operation.LINT: "Lint",
    Operation.INTERPRET: "Interpret",
    Operation.TYPECHECK: "Type-check",
    Operation.COMPILE: "Compile",
    Operation.EXECUTE: "Execute",
}


class Rejected(Exception):
    """A requested change or action is not allowed in the current state."""


@dataclass(frozen=True)
class Source:
    name: str
    text: str
    revision: int


def validate_text(text: str) -> None:
    if not text.strip():
        raise Rejected("Source is empty or whitespace only.")
    size = len(text.encode("utf-8"))
    if size > MAX_SOURCE_BYTES:
        raise Rejected(f"Source is {size} bytes; the limit is {MAX_SOURCE_BYTES} bytes.")


def decode_upload(data: bytes) -> str:
    if len(data) > MAX_SOURCE_BYTES:
        raise Rejected(f"File is {len(data)} bytes; the limit is {MAX_SOURCE_BYTES} bytes.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exn:
        raise Rejected(f"File is not valid UTF-8 text (byte {exn.start}).") from None


class WorkbenchModel:
    def __init__(self) -> None:
        self.source: Source | None = None      # the applied source
        self.draft_name = "Manual input"
        self.draft_text = ""                   # editor contents (maybe unapplied)
        self.results: list[OpResult] = []      # results for source.revision only
        self.artifact: Artifact | None = None
        self.busy: Operation | None = None
        self.notice: tuple[str, str] | None = None   # (level, text)
        self._next_revision = 1

    # ---- derived state -------------------------------------------------

    @property
    def revision(self) -> int:
        return self.source.revision if self.source else 0

    @property
    def dirty(self) -> bool:
        applied = self.source.text if self.source else ""
        return self.draft_text != applied

    def action_state(self, op: Operation) -> tuple[bool, str]:
        """(enabled, reason-if-disabled) for one action button."""
        if self.busy is not None:
            return False, f"Busy: {ACTION_LABELS[self.busy]} is running."
        if self.source is None:
            return False, "Load or apply source first."
        if self.dirty:
            return False, "Apply or discard your edits first."
        if op is Operation.EXECUTE:
            if self.artifact is None or self.artifact.revision != self.revision:
                return False, ("Execute runs generated code from Compile; compilation "
                               "is not yet implemented, so no artifact exists.")
        return True, ""

    # ---- source changes ------------------------------------------------

    def _require_idle(self) -> None:
        if self.busy is not None:
            raise Rejected(f"{ACTION_LABELS[self.busy]} is running; wait for it to finish.")

    def _require_clean(self) -> None:
        if self.dirty:
            raise Rejected("You have unapplied edits. Apply or discard them first.")

    def _install(self, name: str, text: str) -> None:
        self.source = Source(name, text, self._next_revision)
        self._next_revision += 1
        self.draft_name, self.draft_text = name, text
        self.results = []
        self.artifact = None

    def load(self, name: str, text: str) -> None:
        """Replace the applied source (upload or canned example)."""
        self._require_idle()
        self._require_clean()
        validate_text(text)
        self._install(name, text)
        self.notice = ("info", f"Loaded {name} as revision {self.revision}.")

    def load_upload(self, name: str, data: bytes) -> None:
        self._require_idle()
        self._require_clean()
        self.load(name, decode_upload(data))

    def start_manual(self) -> None:
        """Open a blank editor; the applied source stays until Apply."""
        self._require_idle()
        self._require_clean()
        self.draft_name, self.draft_text = "Manual input", ""
        self.notice = ("info", "Blank editor opened. Type an expression and Apply.")

    def edit(self, text: str) -> None:
        self._require_idle()
        self.draft_text = text

    def apply(self) -> None:
        self._require_idle()
        if not self.dirty:
            raise Rejected("There are no edits to apply.")
        validate_text(self.draft_text)   # on failure the draft is kept for correction
        self._install(self.draft_name, self.draft_text)
        self.notice = ("info", f"Applied edits as revision {self.revision}.")

    def discard(self) -> None:
        self._require_idle()
        if self.source:
            self.draft_name, self.draft_text = self.source.name, self.source.text
        else:
            self.draft_name, self.draft_text = "Manual input", ""
        self.notice = ("info", "Edits discarded.")

    def reject(self, message: str) -> None:
        self.notice = ("error", message)

    # ---- actions -------------------------------------------------------

    def begin(self, op: Operation) -> Source:
        enabled, reason = self.action_state(op)
        if not enabled:
            raise Rejected(f"{ACTION_LABELS[op]} is unavailable: {reason}")
        self.busy = op
        self.notice = ("info", f"Running {ACTION_LABELS[op]}...")
        assert self.source is not None
        return self.source

    def finish(self, result: OpResult) -> None:
        self.busy = None
        if result.revision != self.revision:
            return  # stale result for an old revision: drop it
        self.results.append(result)
        if result.operation is Operation.COMPILE:
            # A successful compile replaces the artifact; anything else invalidates it.
            ok = result.status is Status.OK and result.artifact is not None
            self.artifact = result.artifact if ok else None
        self.notice = ("info", f"{ACTION_LABELS[result.operation]} finished: {result.summary}")

    # ---- view-facing snapshot ------------------------------------------

    def snapshot(self) -> dict:
        actions = []
        for op in ACTION_ORDER:
            enabled, reason = self.action_state(op)
            actions.append({"id": op.value, "label": ACTION_LABELS[op],
                            "enabled": enabled, "reason": reason})
        return {
            "source": (None if self.source is None else
                       {"name": self.source.name, "revision": self.source.revision,
                        "text": self.source.text}),
            "draft": {"name": self.draft_name, "text": self.draft_text},
            "dirty": self.dirty,
            "busy": None if self.busy is None else ACTION_LABELS[self.busy],
            "can_replace_source": self.busy is None and not self.dirty,
            "actions": actions,
            "results": [{"operation": ACTION_LABELS[r.operation], "revision": r.revision,
                         "status": r.status.value, "summary": r.summary,
                         "output": r.output} for r in self.results],
            "artifact": (None if self.artifact is None else
                         {"revision": self.artifact.revision,
                          "target": self.artifact.target}),
            "notice": (None if self.notice is None else
                       {"level": self.notice[0], "text": self.notice[1]}),
            "max_source_bytes": MAX_SOURCE_BYTES,
        }
