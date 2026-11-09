"""Run LAMBDA3 interpretation in a worker process with a hard deadline.

The LAMBDA3 interpreter is recursive and has no step budget, so the only
reliable way to stop a long computation is to run it in a separate process
and terminate that process. Each call gets a fresh `spawn`ed process:

    parent                               worker
    ------                               ------
    start process  ───────────────────▶  start up
                   ◀── "ready" ────────  (startup is not charged to the deadline)
    wait ≤ timeout                       parse + type-check + d0exp_evaluate
                   ◀── result/error ───  d0val_format(value)
    terminate if still running

Only plain strings cross the process boundary; LAMBDA3 closures and
environments never leave the worker.
"""

import io
import logging
import multiprocessing
import sys
import threading
import traceback
from contextlib import redirect_stdout

from .errors import (EXECUTION_ERROR, EXECUTION_TIMEOUT, INTERNAL_ERROR,
                     RESOURCE_LIMIT, RpcError)

log = logging.getLogger("lambda_rpc")

_WORKER_STACK_BYTES = 128 * 1024 * 1024  # Windows rejects 256 MiB
# Exceptions LAMBDA3's interpreter raises for well-typed programs that fail at
# run time (list_head of an empty list, 1 / 0, array index out of range, ...).
_RUNTIME_ERRORS = (ValueError, ArithmeticError, IndexError)


def _evaluate(source: str, libraries: tuple[str, ...]) -> tuple:
    """Body of the worker. Returns a small tagged tuple of plain strings."""
    try:
        from . import backend  # imported in the worker, never pickled
        expression, _ = backend.build(source, libraries)
        with redirect_stdout(io.StringIO()):  # LAMBDA `print` output is discarded
            value = backend.L.d0exp_evaluate(expression)
    except RecursionError:
        return ("recursion",)
    except _RUNTIME_ERRORS as error:
        return ("runtime", type(error).__name__, str(error)[:300])
    except BaseException:  # details go to the server log only
        return ("internal", traceback.format_exc())
    try:
        return ("ok", backend.L.d0val_format(value))
    except ValueError:  # e.g. an integer with more digits than Python will print
        return ("too_large",)
    except RecursionError:
        return ("recursion",)
    except BaseException:
        return ("internal", traceback.format_exc())


def _worker_main(conn, source, libraries, recursion_limit):
    conn.send(("ready",))
    outcome = []
    # A large thread stack lets deep (but finite) recursion finish instead of
    # crashing the process.
    sys.setrecursionlimit(recursion_limit)
    try:
        threading.stack_size(_WORKER_STACK_BYTES)
    except ValueError:  # platform refuses this size; keep the default stack
        pass
    thread = threading.Thread(target=lambda: outcome.append(_evaluate(source, libraries)))
    thread.start()
    thread.join()
    conn.send(outcome[0] if outcome else ("internal", "worker thread produced no result"))
    conn.close()


class ProcessInterpreter:
    """Callable `(source, libraries) -> formatted value`, with a deadline."""

    def __init__(self, timeout: float, *, startup_timeout: float = 20.0,
                 max_value_chars: int = 1024 * 1024, recursion_limit: int = 100_000):
        self.timeout = timeout
        self.startup_timeout = startup_timeout
        self.max_value_chars = max_value_chars
        self.recursion_limit = recursion_limit
        self._context = multiprocessing.get_context("spawn")

    def __call__(self, source: str, libraries: tuple[str, ...] = ()) -> str:
        receiver, sender = self._context.Pipe(duplex=False)
        process = self._context.Process(
            target=_worker_main,
            args=(sender, source, tuple(libraries), self.recursion_limit),
            daemon=True,
        )
        process.start()
        sender.close()
        try:
            if not receiver.poll(self.startup_timeout):
                raise RuntimeError("interpreter worker did not start in time")
            receiver.recv()  # "ready": the deadline starts now
            if not receiver.poll(self.timeout):
                raise RpcError(
                    EXECUTION_TIMEOUT,
                    f"Interpretation exceeded the {self.timeout:g} second limit and was stopped",
                    {"timeoutSeconds": self.timeout,
                     "note": "A timeout does not prove that the program never terminates."},
                )
            outcome = receiver.recv()
        except EOFError:
            raise RuntimeError(
                f"interpreter worker exited unexpectedly (exit code {process.exitcode})"
            ) from None
        finally:
            if process.is_alive():
                process.terminate()
            process.join(5)
            receiver.close()
        return self._unpack(outcome)

    def _unpack(self, outcome: tuple) -> str:
        kind = outcome[0]
        if kind == "ok":
            value = outcome[1]
            if len(value) > self.max_value_chars:
                raise RpcError(RESOURCE_LIMIT, "Formatted value is too large to return",
                               {"limit": "maxValueChars", "maxValueChars": self.max_value_chars})
            return value
        if kind == "too_large":
            raise RpcError(RESOURCE_LIMIT, "Value is too large to format",
                           {"limit": "maxValueChars", "maxValueChars": self.max_value_chars})
        if kind == "recursion":
            raise RpcError(RESOURCE_LIMIT, "Interpretation exceeded the recursion depth limit",
                           {"limit": "recursionDepth"})
        if kind == "runtime":
            raise RpcError(EXECUTION_ERROR, f"LAMBDA runtime error: {outcome[2]}",
                           {"exception": outcome[1], "message": outcome[2]})
        # Unexpected failure inside the worker: log it, return nothing internal.
        log.error("interpreter worker failed:\n%s", outcome[1] if len(outcome) > 1 else outcome)
        raise RpcError(INTERNAL_ERROR)
