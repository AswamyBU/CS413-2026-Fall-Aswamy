"""Solver tests: these run the LAMBDA3 program in queens/queens.lam.

Both backends execute the same parsed and type-checked AST: the reference
interpreter (lambda3.d0exp_evaluate) and LAMBDA3's own Python compiler
(lambda3.d0exp_compile). No search logic is written in Python.
"""

import itertools
import os
import unittest
from unittest import mock

from queens import solver
from queens.solver import (BACKTRACK, DONE, PLACE, REJECT, SOLUTION, TRY,
                           CompiledBackend, EventStream, InterpretedBackend,
                           L, event_to_json)

# A root failure continuation that crashes if it is ever called. Used to
# prove the end of the search is never reached before it is requested.
FAILING_ROOT = """
failing_root : unit -> Strm[(sint, sint, sint, List[sint])] =
  lam (u: unit) => if 1 / 0 == 0 then empty_events() else empty_events()
"""


def all_events(backend, size):
    stream = EventStream(backend, size)
    events = []
    while (event := stream.next_event()) is not None:
        events.append(event)
    return events


def brute_force_solutions(n):
    """Independent oracle: permutations with no shared diagonal, lexicographic."""
    return [p for p in itertools.permutations(range(n))
            if all(abs(p[i] - p[j]) != j - i for i in range(n) for j in range(i + 1, n))]


class SourceTests(unittest.TestCase):
    def test_solver_parses_and_typechecks(self):
        declarations = solver.load_declarations()
        names = []
        while isinstance(declarations, L.fnlist_cons):
            names.append(declarations.arg1.arg1)
            declarations = declarations.arg2
        for required in ("check_safe", "place", "try_column", "emit_lazy",
                         "on_solution", "root_exhausted", "queens_stream"):
            self.assertIn(required, names)

    def test_ill_typed_extension_is_rejected(self):
        with self.assertRaises(L.TypeCheckError):
            solver.load_declarations("bad : sint = place(1, list_nil())")


class SafetyTests(unittest.TestCase):
    """queen_attacks / check_safe through both backends."""

    @classmethod
    def setUpClass(cls):
        cls.backends = [CompiledBackend(), InterpretedBackend()]

    def attacks(self, backend, column, distance, previous):
        return backend.to_python(backend.call("queen_attacks", column, distance, previous))

    def safe(self, backend, column, board_newest_first):
        # Instantiate the polymorphic CPS checker at answer type bool.
        # The two continuations are LAMBDA3 values built in the same program.
        src = f"check_safe({column}, 1, {lam_list(board_newest_first)}, lam (u: unit) => true, lam (u: unit) => false)"
        return eval_lambda(backend, src)

    def test_same_column(self):
        # Rows are implicit (one queen per row), so the "same line" clash in
        # this representation is the same column; see TESTING.md.
        for b in self.backends:
            self.assertTrue(self.attacks(b, 3, 1, 3))
            self.assertTrue(self.attacks(b, 3, 5, 3))
            self.assertFalse(self.safe(b, 2, [5, 2, 0]))

    def test_diagonal_up_left(self):  # previous queen at column - distance
        for b in self.backends:
            self.assertTrue(self.attacks(b, 4, 2, 2))
            self.assertFalse(self.safe(b, 4, [0, 2]))  # rows [2, 0]: row 0 queen at 4-2

    def test_diagonal_up_right(self):  # previous queen at column + distance
        for b in self.backends:
            self.assertTrue(self.attacks(b, 1, 3, 4))
            self.assertFalse(self.safe(b, 1, [7, 0, 4]))

    def test_safe_placement(self):
        for b in self.backends:
            self.assertFalse(self.attacks(b, 0, 1, 2))
            self.assertTrue(self.safe(b, 1, [3, 0]))       # board rows [0, 3]
            self.assertTrue(self.safe(b, 0, []))           # empty board

    def test_first_queen_on_row_cannot_share_its_row(self):
        # place always adds exactly one queen for the next row.
        for b in self.backends:
            board = b.to_python(b.call("place", 6, [1, 4]))
            self.assertEqual(board, [6, 1, 4])
            self.assertEqual(b.to_python(b.call("board_rows", [6, 1, 4])), [4, 1, 6])

    def test_check_safe_stops_at_first_conflict(self):
        # Trace hook: a conflict with the newest queen means check_safe is
        # entered once and never recurses into the older queens.
        backend = InterpretedBackend()
        with CallTrace() as trace:
            self.assertFalse(eval_lambda(backend,
                "check_safe(3, 1, list_cons(3, list_cons(0, list_cons(5, list_nil()))), "
                "lam (u: unit) => true, lam (u: unit) => false)"))
        self.assertEqual(trace.calls["check_safe"], 1)


class CpsTests(unittest.TestCase):
    """The success/failure continuations drive the search."""

    def test_success_continuation_gets_board_and_resume(self):
        # Call try_column directly on the last row of a 4x4 board with
        # custom continuations written in LAMBDA3.
        child, stream = eval_value(CompiledBackend(),
            "try_column(4, 3, 0, list_cons(3, list_cons(0, list_cons(2, list_nil()))), "
            "on_solution, root_exhausted)")
        events = take(child, stream, 20)
        # board rows [2, 0, 3]; only column 1 is safe in row 3.
        self.assertEqual([(e.name, e.column, e.row) for e in events], [
            ("try", 0, 3), ("reject", 0, 3),
            ("try", 1, 3), ("place", 1, 3),
            ("solution", -1, -1),
            # resume = the failure continuation passed with the solution:
            ("backtrack", 1, 3), ("try", 2, 3), ("reject", 2, 3),
            ("try", 3, 3), ("reject", 3, 3),
            ("done", -1, -1),
        ])
        self.assertEqual(events[4].board, (2, 0, 3, 1))

    def test_failure_resumes_at_next_candidate(self):
        events = all_events(CompiledBackend(), 4)
        # Row 1 on 4x4: col 0 and 1 conflict with (0,0); col 2 is placed;
        # after its subtree fails we backtrack and resume at col 3.
        pairs = [(e.name, e.column, e.row) for e in events[:30]]
        self.assertEqual(pairs[:8], [
            ("try", 0, 0), ("place", 0, 0),
            ("try", 0, 1), ("reject", 0, 1),
            ("try", 1, 1), ("reject", 1, 1),
            ("try", 2, 1), ("place", 2, 1)])
        i = pairs.index(("backtrack", 2, 1))
        self.assertEqual(pairs[i + 1], ("try", 3, 1))
        self.assertEqual(events[i].board, (0,))  # restored board without the queen

    def test_exhausted_row_calls_enclosing_failure_continuation(self):
        events = all_events(CompiledBackend(), 4)
        # Whenever column n-1 of a row is rejected or backtracked, the next
        # event must come from the enclosing branch (a backtrack one row up)
        # or the root (`done`).
        for prev, nxt in zip(events, events[1:]):
            if prev.kind in (REJECT, BACKTRACK) and prev.column == 3:
                if nxt.kind == DONE:
                    self.assertEqual(prev.row, 0)
                else:
                    self.assertEqual((nxt.kind, nxt.row), (BACKTRACK, prev.row - 1))

    def test_answer_type_is_a_stream_not_a_board(self):
        backend = InterpretedBackend()
        value = backend.call("queens_stream", 4)
        self.assertIsInstance(value, L.D0Vlazy)


class SolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events8 = all_events(CompiledBackend(), 8)

    def test_92_distinct_solutions_in_lexicographic_dfs_order(self):
        solutions = [e.board for e in self.events8 if e.kind == SOLUTION]
        self.assertEqual(len(solutions), 92)
        self.assertEqual(len(set(solutions)), 92)
        self.assertEqual(solutions, brute_force_solutions(8))
        self.assertTrue(all(len(b) == 8 for b in solutions))
        self.assertEqual(solutions[0], (0, 4, 7, 5, 2, 6, 1, 3))

    def test_other_sizes_match_oracle(self):
        expected = {4: 2, 5: 10, 6: 4, 7: 40}
        for n, count in expected.items():
            solutions = [e.board for e in all_events(CompiledBackend(), n) if e.kind == SOLUTION]
            self.assertEqual(len(solutions), count, n)
            self.assertEqual(solutions, brute_force_solutions(n), n)

    def test_deterministic(self):
        again = all_events(CompiledBackend(), 8)
        self.assertEqual(again, self.events8)

    def test_done_once_and_last(self):
        kinds = [e.kind for e in self.events8]
        self.assertEqual(kinds.count(DONE), 1)
        self.assertEqual(kinds[-1], DONE)
        self.assertEqual(len(self.events8), 15720 + 2056 + 13664 + 2056 + 92 + 1)

    def test_interpreter_and_compiler_agree(self):
        for n in (4, 5, 6):
            self.assertEqual(all_events(InterpretedBackend(), n),
                             all_events(CompiledBackend(), n), n)
        # 8x8 through the interpreter, up to and past the first solution.
        compiled = self.events8[:1200]
        stream = EventStream(InterpretedBackend(), 8)
        self.assertEqual(stream.take(1200), compiled)

    @unittest.skipUnless(os.environ.get("QUEENS_SLOW_TESTS"), "set QUEENS_SLOW_TESTS=1 (~20 s)")
    def test_full_8x8_with_interpreter(self):
        self.assertEqual(all_events(InterpretedBackend(), 8), self.events8)


class EventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = all_events(CompiledBackend(), 8)

    def test_every_kind_appears(self):
        self.assertEqual({e.kind for e in self.events}, {TRY, PLACE, REJECT, BACKTRACK, SOLUTION, DONE})

    def test_board_snapshots_and_coordinates(self):
        board = ()
        for e in self.events:
            if e.kind == TRY:
                self.assertEqual(e.board, board)
                self.assertEqual(e.row, len(board))
                self.assertTrue(0 <= e.column < 8)
            elif e.kind == PLACE:
                self.assertEqual(e.board, board + (e.column,))
                self.assertEqual(e.row, len(board))
                board = e.board
            elif e.kind == REJECT:
                self.assertEqual(e.board, board)
                self.assertEqual(e.row, len(board))
                self.assertTrue(attacked(board, e.column))
            elif e.kind == BACKTRACK:
                self.assertEqual(board[:-1], e.board)
                self.assertEqual((e.row, e.column), (len(board) - 1, board[-1]))
                board = e.board
            elif e.kind == SOLUTION:
                self.assertEqual(e.board, board)
                self.assertEqual(len(board), 8)
            else:
                self.assertEqual(e.board, ())
                self.assertEqual(board, ())
        # The previous event of every try was either a place/backtrack/reject/
        # the start, never a solution (solutions are followed by backtrack).
        for prev, nxt in zip(self.events, self.events[1:]):
            if prev.kind == SOLUTION:
                self.assertEqual(nxt.kind, BACKTRACK)

    def test_place_only_when_safe(self):
        for e in self.events:
            if e.kind == PLACE:
                self.assertFalse(attacked(e.board[:-1], e.column))

    def test_json_encoding(self):
        by_kind = {}
        for e in self.events:
            by_kind.setdefault(e.kind, e)
        self.assertEqual(event_to_json(by_kind[TRY]), {"event": "try", "column": 0, "row": 0, "board": []})
        self.assertEqual(event_to_json(by_kind[PLACE]), {"event": "place", "column": 0, "row": 0, "board": [0]})
        self.assertEqual(event_to_json(by_kind[REJECT]), {"event": "reject", "column": 0, "row": 1, "board": [0]})
        self.assertEqual(event_to_json(by_kind[BACKTRACK])["event"], "backtrack")
        self.assertEqual(event_to_json(by_kind[SOLUTION]),
                         {"event": "solution", "board": [0, 4, 7, 5, 2, 6, 1, 3]})
        self.assertEqual(event_to_json(by_kind[DONE]), {"event": "done"})


class LazinessTests(unittest.TestCase):
    def test_constructing_stream_runs_no_thunk_and_no_search(self):
        backend = CompiledBackend()
        stream = EventStream(backend, 10)
        self.assertEqual(backend.thunks_forced, 0)
        self.assertFalse(backend.is_forced(stream._cursor))

        interp = InterpretedBackend()
        with CallTrace() as trace:
            EventStream(interp, 10)
        self.assertEqual(trace.calls["try_column"], 0)
        self.assertEqual(trace.calls["check_safe"], 0)

    def test_forcing_one_cell_leaves_tail_unforced(self):
        backend = InterpretedBackend()
        lazy = backend.call("queens_stream", 8)
        with CallTrace() as trace:
            event, tail = backend.force(lazy)
        self.assertEqual(event.name, "try")
        self.assertTrue(backend.is_forced(lazy))
        self.assertFalse(backend.is_forced(tail))
        self.assertEqual(trace.calls["try_column"], 1)
        self.assertEqual(trace.calls["check_safe"], 0)  # the safety check is the tail's work

    def test_bounded_prefix_does_bounded_work(self):
        backend = CompiledBackend()
        stream = EventStream(backend, 10)
        events = stream.take(5)
        self.assertEqual(len(events), 5)
        self.assertFalse(backend.is_forced(stream._cursor))
        # Each event costs exactly two thunks: its cell and the tail that
        # leads to it. The rest of the 10x10 tree (~200k events) is untouched.
        self.assertEqual(backend.thunks_forced, 2 * 5)
        stream.take(32)
        self.assertEqual(backend.thunks_forced, 2 * 37)

    def test_delayed_failure_in_root_continuation_is_never_reached_early(self):
        for backend_type in (CompiledBackend, InterpretedBackend):
            backend = backend_type(FAILING_ROOT, ("failing_root",))
            cursor = backend.open_with(4, "failing_root")
            seen = []
            while True:
                try:
                    forced = backend.force(cursor)
                except ZeroDivisionError:
                    break
                event, cursor = forced
                seen.append(event)
            # Everything up to the final row-0 backtrack was produced; only
            # asking for the event after it ran the failing root continuation.
            kinds = [e.kind for e in seen]
            self.assertEqual(kinds.count(SOLUTION), 2)
            self.assertEqual((seen[-1].kind, seen[-1].row, seen[-1].column), (BACKTRACK, 0, 3))
            self.assertNotIn(DONE, kinds)

    def test_large_board_prefix_is_fast(self):
        import time
        backend = CompiledBackend()
        start = time.perf_counter()
        stream = EventStream(backend, 10)
        stream.take(32)
        self.assertLess(time.perf_counter() - start, 0.5)


# ----------------------------------------------------------------- helpers

def attacked(board, column):
    row = len(board)
    return any(c == column or abs(c - column) == row - r for r, c in enumerate(board))


def lam_list(items):
    src = "list_nil()"
    for x in reversed(items):
        src = f"list_cons({x}, {src})"
    return src


def eval_lambda(backend, source):
    child, value = eval_value(backend, source)
    return child.to_python(value)


def eval_value(backend, source):
    """Evaluate a LAMBDA3 expression in the scope of queens.lam.

    Returns (backend, value): the expression is added as one more checked
    declaration, so the value belongs to a fresh backend of the same kind
    (compiled lazies can only be forced by the program that made them).
    """
    child = type(backend)(f"_test_value = {source}", ("_test_value",))
    return child, child.function("_test_value")


def take(backend, stream, n):
    out = []
    for _ in range(n):
        forced = backend.force(stream)
        if forced is None:
            break
        event, stream = forced
        out.append(event)
    return out


class CallTrace:
    """Trace hook for the interpreter: counts applications of named fix functions."""

    def __init__(self):
        self.calls = {"try_column": 0, "check_safe": 0}

    def __enter__(self):
        original = L._d0val_apply

        def traced(dfun, darg):
            if isinstance(dfun, L.D0Vfix) and dfun.arg2.arg1 in self.calls:
                self.calls[dfun.arg2.arg1] += 1
            return original(dfun, darg)

        self._patch = mock.patch.object(L, "_d0val_apply", traced)
        self._patch.__enter__()
        return self

    def __exit__(self, *exc):
        return self._patch.__exit__(*exc)


if __name__ == "__main__":
    unittest.main()
