"""Language-tool backend: the adapter between the workbench and lambda1.py.

Nothing in this module knows about HTTP, HTML, or the workbench model.
Every operation takes plain inputs and returns an ``OpResult``.  The
controller only depends on the ``LanguageBackend`` protocol, so tests (or a
future real compiler) can substitute a different implementation.
"""

from __future__ import annotations

import multiprocessing as mp
from multiprocessing.connection import wait as mp_wait
import sys
import threading

import lambda1 as L
from contract import Artifact, OpResult, Operation, Status
from reader import ReadError, read_d0exp


########################################################################
# Helpers shared by the real backend (also importable by tests).

def free_variables(source: str) -> frozenset[str]:
    """Read ``source`` and return its free variables via d0exp_fvset."""
    return L.d0exp_fvset(read_d0exp(source))


def contains_error_value(val: L.D0V000) -> bool:
    """True if ``val`` is the D0V000() error sentinel, directly or in a pair."""
    if type(val) is L.D0V000:
        return True
    if isinstance(val, L.D0Vpair):
        return contains_error_value(val.arg1) or contains_error_value(val.arg2)
    return False


def format_value(val: L.D0V000) -> str:
    """Render a value as text; closures are summarised instead of dumping env."""
    if isinstance(val, L.D0Vpair):
        return f"D0Vpair(arg1={format_value(val.arg1)}, arg2={format_value(val.arg2)})"
    if isinstance(val, L.D0Vlam):
        return f"D0Vlam(<closure: lam {val.arg2.arg1}. ...>)"
    if isinstance(val, L.D0Vfix):
        return f"D0Vfix(<closure: fix {val.arg2.arg1}({val.arg2.arg2}). ...>)"
    return repr(val)


# Evaluation runs in a child process so a non-terminating program can be
# killed.  Inside the child, a large thread stack + recursion limit lets the
# recursive evaluator handle reasonably deep (but finite) recursion.
CHILD_RECURSION_LIMIT = 20_000
CHILD_STACK_BYTES = 64 * 1024 * 1024


def _evaluate_in_child(source: str, conn) -> None:
    def work():
        try:
            val = L.d0exp_evaluate(read_d0exp(source), L.ENVnil())
            if contains_error_value(val):
                conn.send(("runtime", "evaluation produced the error value D0V000() "
                                      "(an unbound variable was looked up)",
                           format_value(val)))
            else:
                conn.send(("ok", format_value(val), ""))
        except ReadError as exn:
            conn.send(("input", str(exn), ""))
        except RecursionError:
            conn.send(("runtime", "recursion too deep (stack limit reached)", ""))
        except ZeroDivisionError:
            conn.send(("runtime", "division by zero", ""))
        except Exception as exn:  # TypeError etc. raised by d0exp_evaluate
            conn.send(("runtime", f"{type(exn).__name__}: {exn}", ""))

    sys.setrecursionlimit(CHILD_RECURSION_LIMIT)
    threading.stack_size(CHILD_STACK_BYTES)
    t = threading.Thread(target=work)
    t.start()
    t.join()
    conn.close()


class Lambda1Backend:
    """Real backend: Lint and Interpret use lambda1.py; others are placeholders."""

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds

    def lint(self, source: str, revision: int) -> OpResult:
        op = Operation.LINT
        try:
            fvs = free_variables(source)
        except ReadError as exn:
            return OpResult(op, revision, Status.INPUT_ERROR, "Invalid input", str(exn))
        except RecursionError:
            return OpResult(op, revision, Status.BACKEND_FAILURE,
                            "Lint failed", "expression too deep to analyse")
        if fvs:
            names = sorted(fvs)
            return OpResult(op, revision, Status.LANGUAGE_ERROR,
                            f"Undeclared variable(s): {', '.join(names)}",
                            "Free (undeclared) variables:\n" +
                            "\n".join(f"  {n}" for n in names))
        return OpResult(op, revision, Status.OK, "No free variables found",
                        "The expression is closed: every variable is declared.")

    def interpret(self, source: str, revision: int) -> OpResult:
        op = Operation.INTERPRET
        # Reading first in-process gives fast, precise input errors.
        try:
            read_d0exp(source)
        except ReadError as exn:
            return OpResult(op, revision, Status.INPUT_ERROR, "Invalid input", str(exn))

        ctx = mp.get_context("spawn")
        parent, child = ctx.Pipe(duplex=False)
        proc = ctx.Process(target=_evaluate_in_child, args=(source, child), daemon=True)
        try:
            proc.start()
            child.close()
            # Wake on a result *or* on the child exiting, whichever is first.
            ready = mp_wait([parent, proc.sentinel], self.timeout_seconds)
            if not ready:
                return OpResult(op, revision, Status.BACKEND_FAILURE,
                                "Interpretation timed out",
                                f"Stopped after {self.timeout_seconds:g} s; the program "
                                "may not terminate. Edit the source or retry.")
            try:
                has_result = parent.poll()
            except OSError:          # Windows reports a closed pipe this way
                has_result = False
            if not has_result:
                proc.join(1)
                raise EOFError(f"interpreter process exited (code {proc.exitcode}) "
                               "without a result")
            kind, message, detail = parent.recv()
        except (EOFError, OSError) as exn:
            return OpResult(op, revision, Status.BACKEND_FAILURE,
                            "Interpreter process failed", str(exn) or "no result received")
        finally:
            if proc.is_alive():
                proc.kill()
            proc.join(1)
            parent.close()

        if kind == "ok":
            return OpResult(op, revision, Status.OK, "Evaluated", message)
        if kind == "input":
            return OpResult(op, revision, Status.INPUT_ERROR, "Invalid input", message)
        text = f"Runtime error: {message}" + (f"\nValue: {detail}" if detail else "")
        return OpResult(op, revision, Status.LANGUAGE_ERROR, "Runtime error", text)

    def typecheck(self, source: str, revision: int) -> OpResult:
        return OpResult(Operation.TYPECHECK, revision, Status.NOT_IMPLEMENTED,
                        "Type checking is not yet implemented",
                        "No type analysis was performed on this source.")

    def compile(self, source: str, revision: int) -> OpResult:
        return OpResult(Operation.COMPILE, revision, Status.NOT_IMPLEMENTED,
                        "Compilation is not yet implemented",
                        "No code was generated, so Execute stays unavailable.")

    def execute(self, artifact: Artifact | None, revision: int) -> OpResult:
        if artifact is None or artifact.revision != revision:
            return OpResult(Operation.EXECUTE, revision, Status.UNAVAILABLE,
                            "No generated code to execute",
                            "Execute runs code produced by Compile. Compilation is "
                            "not yet implemented, so no artifact exists.")
        return OpResult(Operation.EXECUTE, revision, Status.NOT_IMPLEMENTED,
                        "Execution of generated code is not yet implemented")
