"""Workbench controller: turns user intents into model updates and backend calls.

The controller is framework-independent: app.py (Flask) translates HTTP
requests into these method calls, and tests call them directly with a fake
backend.  Every method returns the model snapshot that the view renders.
"""

from __future__ import annotations

import threading
from pathlib import Path

from contract import LanguageBackend, OpResult, Operation, Status
from model import Rejected, WorkbenchModel

EXAMPLES_DIR = Path(__file__).parent / "examples"
CANNED_EXAMPLES = {           # key -> (display name, file)
    "factorial": ("Factorial", EXAMPLES_DIR / "factorial.lambda"),
    "fibonacci": ("Fibonacci", EXAMPLES_DIR / "fibonacci.lambda"),
}


class WorkbenchController:
    def __init__(self, model: WorkbenchModel, backend: LanguageBackend) -> None:
        self.model = model
        self.backend = backend
        # Guards the model; held only while reading/updating state, never while
        # a backend call runs, so the page can still fetch state during work.
        self._lock = threading.Lock()

    def _change(self, fn) -> dict:
        with self._lock:
            try:
                fn()
            except Rejected as exn:
                self.model.reject(str(exn))
            return self.model.snapshot()

    # ---- source intents ------------------------------------------------

    def state(self) -> dict:
        with self._lock:
            return self.model.snapshot()

    def upload(self, filename: str, data: bytes) -> dict:
        name = Path(filename or "upload").name
        return self._change(lambda: self.model.load_upload(name, data))

    def choose_example(self, key: str) -> dict:
        def go():
            if key not in CANNED_EXAMPLES:
                raise Rejected(f"Unknown example {key!r}.")
            name, path = CANNED_EXAMPLES[key]
            self.model.load(name, path.read_text(encoding="utf-8"))
        return self._change(go)

    def manual_input(self) -> dict:
        return self._change(self.model.start_manual)

    def edit(self, text: str) -> dict:
        return self._change(lambda: self.model.edit(text))

    def apply(self) -> dict:
        return self._change(self.model.apply)

    def discard(self) -> dict:
        return self._change(self.model.discard)

    def reject(self, message: str) -> dict:
        """Record a change rejected before reaching the model (e.g. HTTP 413)."""
        with self._lock:
            self.model.reject(message)
            return self.model.snapshot()

    # ---- action intents ------------------------------------------------

    def run(self, op_name: str) -> dict:
        try:
            op = Operation(op_name)
        except ValueError:
            with self._lock:
                self.model.reject(f"Unknown action {op_name!r}.")
                return self.model.snapshot()

        with self._lock:
            try:
                source = self.model.begin(op)     # marks the model busy
            except Rejected as exn:
                self.model.reject(str(exn))
                return self.model.snapshot()
            artifact = self.model.artifact

        result = self._dispatch(op, source.text, source.revision, artifact)

        with self._lock:
            self.model.finish(result)             # always clears busy
            return self.model.snapshot()

    def _dispatch(self, op, text, revision, artifact) -> OpResult:
        try:
            match op:
                case Operation.LINT:
                    return self.backend.lint(text, revision)
                case Operation.INTERPRET:
                    return self.backend.interpret(text, revision)
                case Operation.TYPECHECK:
                    return self.backend.typecheck(text, revision)
                case Operation.COMPILE:
                    return self.backend.compile(text, revision)
                case Operation.EXECUTE:
                    return self.backend.execute(artifact, revision)
        except Exception as exn:   # the backend itself broke: report, keep source
            return OpResult(op, revision, Status.BACKEND_FAILURE,
                            "Backend failure", f"{type(exn).__name__}: {exn}")
        raise AssertionError(op)
