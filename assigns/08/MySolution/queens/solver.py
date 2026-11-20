"""Bridge between Python and the LAMBDA3 queen solver in queens.lam.

This module knows nothing about HTTP or JSON-RPC. It loads and type-checks
queens.lam once, then runs it with one of two backends that execute the same
checked AST:

* ``CompiledBackend``    -- LAMBDA3's own Python code generator
                            (``lambda3.d0exp_compile``); the default, because
                            it is roughly 150x faster than the tree walker.
* ``InterpretedBackend`` -- the reference interpreter (``lambda3.d0exp_evaluate``).

Neither backend contains search logic. Python only forces one stream cell at
a time (``force``) and copies the event tuple out into plain Python values.
No interpreter environment, closure or lazy value ever leaves this module
through ``EventStream``.
"""

from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

MIN_SIZE = 4
MAX_SIZE = 10
EVENT_KINDS = ("try", "place", "reject", "backtrack", "solution", "done")
TRY, PLACE, REJECT, BACKTRACK, SOLUTION, DONE = range(6)

SOLVER_SOURCE = Path(__file__).with_name("queens.lam")
# Names exported from queens.lam to Python.
EXPORTS = ("queens_stream", "queens_stream_with", "check_safe", "queen_attacks",
           "place", "board_rows", "on_solution", "root_exhausted",
           "empty_events", "try_column")


def _lambda3_dir() -> Path:
    configured = os.environ.get("QUEENS_LAMBDA3_DIR")
    if configured:
        return Path(configured).resolve()
    # MySolution/queens/solver.py -> assigns/08/LAMBDA3
    return Path(__file__).resolve().parents[2] / "LAMBDA3"


def _import_lambda3():
    directory = str(_lambda3_dir())
    if directory not in sys.path:
        # lambda3.py imports its sibling basics0.py as a top-level module.
        sys.path.insert(0, directory)
    import lambda3
    return lambda3


L = _import_lambda3()


@dataclass(frozen=True)
class Event:
    """One search event as plain Python data (never a LAMBDA value)."""
    kind: int
    column: int
    row: int
    board: tuple[int, ...]

    @property
    def name(self) -> str:
        return EVENT_KINDS[self.kind]


@lru_cache(maxsize=None)
def load_declarations(extra_source: str = ""):
    """Parse and type-check queens.lam (plus optional extra declarations).

    Raises lambda3.LambdaSyntaxError / lambda3.TypeCheckError on bad source.
    The result is cached; the solver source is fixed at deploy time.
    """
    source = SOLVER_SOURCE.read_text(encoding="utf-8")
    if extra_source:
        source += "\n" + extra_source
    declarations = L.d0cls_parse(source)
    L.d0cls_typecheck(declarations)
    return declarations


def _export_tuple(names: tuple[str, ...]):
    return L.D0Etupl(tuple(L.D0Evar(name) for name in names))


class Backend:
    """Common interface: open a stream, force one cell, call exported functions."""

    name = "abstract"

    def __init__(self, extra_source: str = "", extra_exports: tuple[str, ...] = ()):
        self.declarations = load_declarations(extra_source)
        self.exports = EXPORTS + tuple(extra_exports)

    def open(self, size: int):
        return self.call("queens_stream", size)

    def open_with(self, size: int, root_name: str):
        return self.call("queens_stream_with", size, self.function(root_name))

    # Subclasses implement:
    def function(self, name: str): raise NotImplementedError
    def call(self, name: str, *args): raise NotImplementedError
    def force(self, stream) -> tuple[Event, object] | None: raise NotImplementedError
    def is_forced(self, stream) -> bool: raise NotImplementedError
    def to_python(self, value): raise NotImplementedError


class CompiledBackend(Backend):
    """Runs the checked program through lambda3.d0exp_compile + exec."""

    name = "compiled"

    def __init__(self, extra_source: str = "", extra_exports: tuple[str, ...] = ()):
        super().__init__(extra_source, extra_exports)
        # Counts every suspended LAMBDA3 thunk the solver runs (stream cells
        # and tails). Tests use it to prove that unrequested work never ran.
        # (The interpreter backend is observed with a call-trace hook instead.)
        self.thunks_forced = 0
        self._counter_lock = threading.Lock()
        program = L.d0exp_compile(L.D0Elets(self.declarations, _export_tuple(self.exports)))
        namespace: dict[str, object] = {}
        exec(compile(program, "<queens.lam compiled>", "exec"), namespace)
        self._ns = namespace
        self._values = dict(zip(self.exports, namespace["_lambda_result"]))
        self._lazy_type = namespace["_LambdaLazy"]
        original_eval = namespace["_lambda_lazy_eval"]

        def counting_eval(value):
            # Same semantics as the runtime's lazy_eval, plus a counter.
            if isinstance(value, self._lazy_type) and not value.evaluated:
                with self._counter_lock:
                    self.thunks_forced += 1
            return original_eval(value)

        # Generated code looks _lambda_lazy_eval up in this namespace at call
        # time, so the hook sees every force made by the solver itself.
        namespace["_lambda_lazy_eval"] = counting_eval
        self._lazy_eval = counting_eval

    def function(self, name: str):
        return self._values[name]

    def call(self, name: str, *args):
        argument = args[0] if len(args) == 1 else tuple(args)
        return self._values[name](argument)

    def force(self, stream):
        cell = self._lazy_eval(stream)
        if not cell["cons"]:
            return None
        kind, column, row, board = cell["head"]
        return Event(kind, column, row, tuple(board)), cell["tail"]

    def is_forced(self, stream) -> bool:
        return stream.evaluated

    def to_python(self, value):
        return value


class InterpretedBackend(Backend):
    """Runs the checked program with the reference interpreter."""

    name = "interpreter"

    def __init__(self, extra_source: str = "", extra_exports: tuple[str, ...] = ()):
        super().__init__(extra_source, extra_exports)
        values = L.d0exp_evaluate(L.D0Elets(self.declarations, _export_tuple(self.exports)))
        self._values = dict(zip(self.exports, values.arg1))
        self._force_expr = L.D0Eop1("lazy_eval", L.D0Evar("s"))
        self._apply_expr = L.D0Eapp(L.D0Evar("f"), L.D0Evar("x"))

    def function(self, name: str):
        return self._values[name]

    def _to_value(self, item):
        if isinstance(item, bool):
            return L.D0Vbtf(item)
        if isinstance(item, int):
            return L.D0Vint(item)
        if isinstance(item, tuple):
            return L.D0Vtupl(tuple(self._to_value(x) for x in item))
        if isinstance(item, list):
            items = L.fnlist_nil()
            for x in reversed(item):
                items = L.fnlist_cons(self._to_value(x), items)
            return L.D0Vlist(items)
        if isinstance(item, L.D0V000):
            return item
        raise TypeError(f"cannot pass {type(item).__name__} to LAMBDA3")

    def call(self, name: str, *args):
        argument = self._to_value(args[0] if len(args) == 1 else tuple(args))
        env = L.ENVcns("f", self._values[name], L.ENVcns("x", argument, L.ENVnil()))
        return L.d0exp_evaluate(self._apply_expr, env)

    def force(self, stream):
        cell = L.d0exp_evaluate(self._force_expr, L.ENVcns("s", stream, L.ENVnil()))
        if not cell.is_cons:
            return None
        kind, column, row, board = (self.to_python(v) for v in cell.head.arg1)
        return Event(kind, column, row, tuple(board)), cell.tail

    def is_forced(self, stream) -> bool:
        return stream.evaluated

    def to_python(self, value):
        if isinstance(value, L.D0Vint):
            return value.arg1
        if isinstance(value, L.D0Vbtf):
            return value.arg1
        if isinstance(value, L.D0Vtupl):
            return tuple(self.to_python(v) for v in value.arg1)
        if isinstance(value, L.D0Vlist):
            out, items = [], value.arg1
            while isinstance(items, L.fnlist_cons):
                out.append(self.to_python(items.arg1))
                items = items.arg2
            return out
        return value  # closures/lazies stay opaque


BACKENDS: dict[str, Callable[[], Backend]] = {
    "compiled": CompiledBackend,
    "interpreter": InterpretedBackend,
}


def make_backend(name: str = "compiled") -> Backend:
    try:
        return BACKENDS[name]()
    except KeyError:
        raise ValueError(f"unknown backend {name!r}; choose from {sorted(BACKENDS)}") from None


class EventStream:
    """A cursor over one lazy event stream.

    Holds only the *current* unforced stream value. ``next_event`` forces
    exactly one cell and replaces the cursor with that cell's (unforced) tail,
    so earlier cells become garbage and later cells are never touched.
    """

    def __init__(self, backend: Backend, size: int):
        if not (isinstance(size, int) and not isinstance(size, bool)
                and MIN_SIZE <= size <= MAX_SIZE):
            raise ValueError(f"size must be an integer from {MIN_SIZE} to {MAX_SIZE}")
        self.backend = backend
        self.size = size
        self._cursor = backend.open(size)  # no search work happens here
        self.finished = False

    def next_event(self) -> Event | None:
        if self.finished:
            return None
        forced = self.backend.force(self._cursor)
        if forced is None:  # end of stream (only reached after `done`)
            self._release()
            return None
        event, tail = forced
        if event.kind == DONE:
            self._release()
        else:
            self._cursor = tail
        return event

    def take(self, limit: int) -> list[Event]:
        events: list[Event] = []
        while len(events) < limit:
            event = self.next_event()
            if event is None:
                break
            events.append(event)
            if event.kind == DONE:
                break
        return events

    def _release(self) -> None:
        # Drop the reference to the remaining (empty) stream and its closures.
        self.finished = True
        self._cursor = None


def event_to_json(event: Event) -> dict:
    """Convert an Event to the documented JSON-RPC event object."""
    if event.kind == DONE:
        return {"event": "done"}
    if event.kind == SOLUTION:
        return {"event": "solution", "board": list(event.board)}
    return {"event": event.name, "column": event.column, "row": event.row,
            "board": list(event.board)}
