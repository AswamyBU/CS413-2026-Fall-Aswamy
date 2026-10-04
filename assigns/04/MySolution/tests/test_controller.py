"""Tasks 4.5 and 4.6: dispatch, placeholders, busy state, failure and retry.

These tests substitute test backends for Lambda1Backend; the view
(static/) and HTTP layer (app.py) are untouched.
"""

import threading

import pytest

from backend import Lambda1Backend
from conftest import example
from contract import OpResult, Operation, Status
from controller import WorkbenchController
from model import WorkbenchModel


class RecordingBackend:
    def __init__(self):
        self.calls = []

    def _r(self, op, rev):
        self.calls.append(op)
        return OpResult(op, rev, Status.OK, f"{op.value} ran")

    def lint(self, s, rev): return self._r(Operation.LINT, rev)
    def interpret(self, s, rev): return self._r(Operation.INTERPRET, rev)
    def typecheck(self, s, rev): return self._r(Operation.TYPECHECK, rev)
    def compile(self, s, rev): return self._r(Operation.COMPILE, rev)
    def execute(self, a, rev): return self._r(Operation.EXECUTE, rev)


def loaded(backend):
    ctl = WorkbenchController(WorkbenchModel(), backend)
    ctl.choose_example("factorial")
    return ctl


@pytest.mark.parametrize("op", ["lint", "interpret", "typecheck", "compile"])
def test_dispatch_reaches_matching_backend_method(op):
    be = RecordingBackend()
    snap = loaded(be).run(op)
    assert be.calls == [Operation(op)]
    assert snap["results"][-1]["revision"] == snap["source"]["revision"]


def test_execute_is_not_dispatched_without_artifact():
    be = RecordingBackend()
    snap = loaded(be).run("execute")
    assert be.calls == []
    assert snap["notice"]["level"] == "error"
    assert not next(a for a in snap["actions"] if a["id"] == "execute")["enabled"]


def test_unknown_action_and_unknown_example_are_rejected():
    be = RecordingBackend()
    ctl = loaded(be)
    assert ctl.run("format-disk")["notice"]["level"] == "error"
    assert ctl.choose_example("nope")["notice"]["level"] == "error"
    assert be.calls == []


def test_placeholders_never_look_successful_with_real_backend():
    ctl = loaded(Lambda1Backend())
    for op in ("typecheck", "compile"):
        r = ctl.run(op)["results"][-1]
        assert r["status"] == "not_implemented"
        assert "not yet implemented" in r["summary"]
    snap = ctl.state()
    assert snap["artifact"] is None
    execute = next(a for a in snap["actions"] if a["id"] == "execute")
    assert not execute["enabled"] and "Compile" in execute["reason"]


def test_manual_edit_apply_lint_interpret_through_controller():
    ctl = WorkbenchController(WorkbenchModel(), Lambda1Backend())
    ctl.manual_input()
    ctl.edit('D0Evar("x")')
    snap = ctl.apply()
    assert snap["source"]["revision"] == 1
    lint = ctl.run("lint")["results"][-1]
    assert lint["status"] == "language_error" and "x" in lint["summary"]
    ctl.edit('D0Elet("x", D0Eint(41), D0Eop1("+1", D0Evar("x")))')
    snap = ctl.apply()
    assert snap["source"]["revision"] == 2 and snap["results"] == []
    assert ctl.run("lint")["results"][-1]["status"] == "ok"
    assert ctl.run("interpret")["results"][-1]["output"] == "D0Vint(arg1=42)"


class BlockingBackend(RecordingBackend):
    """Interpret blocks until released, so we can observe the busy state."""
    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def interpret(self, s, rev):
        self.started.set()
        self.release.wait(5)
        return self._r(Operation.INTERPRET, rev)


def test_busy_state_blocks_conflicts_and_is_restored():
    be = BlockingBackend()
    ctl = loaded(be)
    done = {}
    t = threading.Thread(target=lambda: done.setdefault("snap", ctl.run("interpret")))
    t.start()
    assert be.started.wait(5)

    snap = ctl.state()                          # state still readable while busy
    assert snap["busy"] == "Interpret"
    assert not any(a["enabled"] for a in snap["actions"])
    assert ctl.run("lint")["notice"]["level"] == "error"
    assert ctl.edit("D0Eint(0)")["notice"]["level"] == "error"
    assert ctl.choose_example("fibonacci")["source"]["name"] == "Factorial"

    be.release.set()
    t.join(5)
    final = done["snap"]
    assert final["busy"] is None
    assert final["results"][-1]["status"] == "ok"
    assert be.calls == [Operation.INTERPRET]    # the conflicting Lint never ran


class FlakyBackend(RecordingBackend):
    """Fails once with an exception, then works."""
    def __init__(self):
        super().__init__()
        self.failed = False

    def interpret(self, s, rev):
        if not self.failed:
            self.failed = True
            raise ConnectionError("interpreter crashed")
        return self._r(Operation.INTERPRET, rev)


def test_backend_exception_reported_then_retry_succeeds():
    ctl = loaded(FlakyBackend())
    snap = ctl.run("interpret")
    r = snap["results"][-1]
    assert r["status"] == "backend_failure" and "interpreter crashed" in r["output"]
    assert snap["busy"] is None and snap["source"]["name"] == "Factorial"
    snap = ctl.run("interpret")
    assert snap["results"][-1]["status"] == "ok"


def test_timeout_then_edit_and_retry_with_real_backend():
    ctl = WorkbenchController(WorkbenchModel(), Lambda1Backend(timeout_seconds=0.5))
    ctl.upload("slow.lambda", example("slow_fibonacci").encode())
    snap = ctl.run("interpret")
    assert snap["results"][-1]["status"] == "backend_failure"
    assert snap["busy"] is None
    assert snap["source"]["text"] == example("slow_fibonacci")   # preserved
    ctl.edit(example("slow_fibonacci").replace("D0Eint(40)", "D0Eint(10)"))
    ctl.apply()
    assert ctl.run("interpret")["results"][-1]["output"] == "D0Vint(arg1=55)"
