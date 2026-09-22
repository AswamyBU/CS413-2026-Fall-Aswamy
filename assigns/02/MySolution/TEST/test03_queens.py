"""Tests for queens_lambda0.py. The N = 8 runs are slow (~30 s), so they're cached."""

import itertools
import sys
import unittest
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # use MySolution/lambda0.py

from lambda0 import (
    T0Mint, T0Mbtf, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0, T0Mop2, T0Mpair,
    t0erm_cbv_evaluate0, t0erm_fvset, t0erm_subst0,
)
import queens_lambda0 as Q
from queens_lambda0 import (
    app, I, V, abs_term, board_get_term, board_set_term, safety_test1_term,
    safety_test2_term, make_board_term, queens_term, run_count, run_all,
    decode_board, is_valid_board, format_board,
)

ev = t0erm_cbv_evaluate0


def board_term(cols):
    term = I(0)
    for c in reversed(cols):
        term = T0Mpair(I(c), term)
    return term


# brute-force reference, in the same (lexicographic) order as the ATS search
def reference_solutions(n):
    return [list(p) for p in itertools.permutations(range(n)) if is_valid_board(list(p), n)]


KNOWN_COUNTS = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92}


@lru_cache(maxsize=None)
def cached_all(n):
    return run_all(n)


@lru_cache(maxsize=None)
def cached_count(n):
    return run_count(n)


class TestTermsAreClosed(unittest.TestCase):
    def test_closed(self):
        for name, term in [
            ("abs", abs_term()), ("board_get", board_get_term()),
            ("board_set", board_set_term()), ("safety_test1", safety_test1_term()),
            ("safety_test2", safety_test2_term()), ("make_board", make_board_term()),
            ("queens (count)", queens_term(False)), ("queens (collect)", queens_term(True)),
        ]:
            with self.subTest(term=name):
                self.assertEqual(t0erm_fvset(term), frozenset())


class TestHelpers(unittest.TestCase):
    def test_abs(self):
        for x in (-5, -1, 0, 1, 5):
            with self.subTest(x=x):
                self.assertEqual(ev(app(abs_term(), I(x))), I(abs(x)))

    def test_make_board(self):
        for k in range(0, 9):
            with self.subTest(k=k):
                self.assertEqual(ev(app(make_board_term(), I(k))), board_term([0] * k))

    def test_board_get(self):
        cols = [3, 1, 4, 1, 5, 9, 2, 6]
        for i, c in enumerate(cols):
            with self.subTest(i=i):
                self.assertEqual(ev(app(board_get_term(), board_term(cols), I(i))), I(c))

    def test_board_get_past_the_end_raises(self):
        with self.assertRaises(TypeError):
            ev(app(board_get_term(), board_term([1, 2, 3]), I(3)))

    def test_board_set(self):
        cols = [0] * 8
        for i in range(8):
            with self.subTest(i=i):
                expected = list(cols)
                expected[i] = 5
                self.assertEqual(ev(app(board_set_term(), board_term(cols), I(i), I(5))),
                                 board_term(expected))

    def test_board_set_is_functional(self):
        bd = board_term([1, 2, 3])
        new = ev(app(board_set_term(), bd, I(1), I(9)))
        self.assertEqual(decode_board(new), [1, 9, 3])
        self.assertEqual(decode_board(bd), [1, 2, 3])


class TestConflictChecks(unittest.TestCase):
    def st1(self, i0, j0, i, j):
        result = ev(app(safety_test1_term(), I(i0), I(j0), I(i), I(j)))
        self.assertIsInstance(result, T0Mbtf)  # comparisons yield T0Mbtf
        return result.arg1

    def test_same_column_is_unsafe(self):
        self.assertFalse(self.st1(0, 3, 5, 3))
        self.assertFalse(self.st1(2, 0, 3, 0))

    def test_same_diagonal_is_unsafe(self):
        self.assertFalse(self.st1(0, 0, 2, 2))   # down-right
        self.assertFalse(self.st1(0, 4, 3, 1))   # down-left
        self.assertFalse(self.st1(5, 5, 1, 1))   # up-left
        self.assertFalse(self.st1(5, 2, 3, 4))   # up-right

    def test_safe_pairs(self):
        self.assertTrue(self.st1(0, 0, 2, 3))    # knight-move apart
        self.assertTrue(self.st1(0, 0, 1, 2))
        self.assertTrue(self.st1(3, 1, 4, 3))

    def test_matches_python_rule_exhaustively(self):
        for i0, j0, i, j in itertools.product(range(4), repeat=4):
            with self.subTest(i0=i0, j0=j0, i=i, j=j):
                expected = j0 != j and abs(i0 - i) != abs(j0 - j)
                self.assertEqual(self.st1(i0, j0, i, j), expected)

    def st2(self, i0, j0, cols, i):
        return ev(app(safety_test2_term(), I(i0), I(j0), board_term(cols), I(i))).arg1

    def test_safety_test2_no_earlier_rows(self):
        self.assertTrue(self.st2(0, 5, [0, 0, 0, 0], -1))

    def test_safety_test2_against_placed_queens(self):
        cols = [1, 3, 0, 2]  # a 4-queens solution
        for j in range(4):
            with self.subTest(j=j):
                expected = all(cols[r] != j and abs(4 - r) != abs(j - cols[r]) for r in range(4))
                self.assertEqual(self.st2(4, j, cols + [0], 3), expected)

    def test_safety_test2_only_checks_rows_up_to_i(self):
        self.assertTrue(self.st2(2, 4, [0, 2, 4], 0))    # row 0 only
        self.assertFalse(self.st2(2, 4, [0, 2, 4], 2))   # includes row 2


class TestSolutionCounts(unittest.TestCase):
    def test_small_boards(self):
        for n in range(1, 8):
            with self.subTest(n=n):
                self.assertEqual(cached_count(n), KNOWN_COUNTS[n])

    def test_eight_queens_has_92_solutions(self):
        # assertloc (nsol = 92) in queens.dats
        self.assertEqual(cached_count(8), 92)


class TestSolutions(unittest.TestCase):
    def test_collecting_and_counting_agree(self):
        for n in range(1, 8):
            with self.subTest(n=n):
                count, boards = cached_all(n)
                self.assertEqual(count, cached_count(n))
                self.assertEqual(len(boards), count)

    def test_boards_are_valid_and_distinct(self):
        for n in range(4, 8):
            with self.subTest(n=n):
                _, boards = cached_all(n)
                for bd in boards:
                    self.assertTrue(is_valid_board(bd, n), bd)
                self.assertEqual(len({tuple(b) for b in boards}), len(boards))

    def test_solutions_in_reference_order_small(self):
        for n in range(1, 8):
            with self.subTest(n=n):
                _, boards = cached_all(n)
                self.assertEqual(boards, reference_solutions(n))

    def test_four_queens_exact(self):
        _, boards = cached_all(4)
        self.assertEqual(boards, [[1, 3, 0, 2], [2, 0, 3, 1]])

    def test_eight_queens_all_solutions(self):
        count, boards = cached_all(8)
        self.assertEqual(count, 92)
        self.assertEqual(len(boards), 92)
        for bd in boards:
            self.assertEqual(len(bd), 8)
            self.assertTrue(is_valid_board(bd, 8), bd)
        self.assertEqual(len({tuple(b) for b in boards}), 92)
        self.assertEqual(boards, reference_solutions(8))
        self.assertEqual(boards[0], [0, 4, 7, 5, 2, 6, 1, 3])
        self.assertEqual(boards[-1], [7, 3, 0, 2, 5, 1, 6, 4])

    def test_invalid_boards_are_rejected_by_the_checker(self):
        self.assertFalse(is_valid_board([0, 1, 2, 3, 4, 5, 6, 7]))  # one diagonal
        self.assertFalse(is_valid_board([0, 0, 0, 0, 0, 0, 0, 0]))  # one column
        self.assertFalse(is_valid_board([0, 4, 7, 5, 2, 6, 1]))     # too few queens
        self.assertFalse(is_valid_board([0, 4, 7, 5, 2, 6, 1, 8]))  # off the board


class TestAgainstATSSource(unittest.TestCase):
    def test_ats_source_is_included_and_expects_92(self):
        source = (ROOT / "queens.dats").read_text()
        self.assertIn("#define N 8", source)
        self.assertIn("assertloc (nsol = 92)", source)

    def test_output_format_matches_ats_print_board(self):
        # print_board (0, 1, ..., 7) is a diagonal
        expected = "".join(". " * k + "Q " + ". " * (7 - k) + "\n" for k in range(8)) + "\n"
        self.assertEqual(format_board(list(range(8))), expected)
        self.assertTrue(format_board([0, 4, 7, 5, 2, 6, 1, 3]).startswith("Q . . . . . . . \n"))


class TestInterpreterAdditions(unittest.TestCase):
    def test_tail_calls_do_not_grow_the_stack(self):
        # loop n acc = if n == 0 then acc else loop (n - 1) (acc + n)
        loop = T0Mfix("loop", "n", T0Mlam("acc", T0Mif0(
            T0Mop2("==", V("n"), I(0)),
            V("acc"),
            app(V("loop"), T0Mop2("-", V("n"), I(1)), T0Mop2("+", V("acc"), V("n"))))))
        self.assertEqual(ev(app(loop, I(20000), I(0))), I(20000 * 20001 // 2))

    def test_non_tail_recursion_still_works(self):
        # sum n = if n == 0 then 0 else n + sum (n - 1)
        total = T0Mfix("sum", "n", T0Mif0(
            T0Mop2("==", V("n"), I(0)), I(0),
            T0Mop2("+", V("n"), T0Mapp(V("sum"), T0Mop2("-", V("n"), I(1))))))
        self.assertEqual(ev(T0Mapp(total, I(50))), I(1275))

    def test_substitution_skips_subterms_without_the_variable(self):
        term = T0Mlam("y", T0Mpair(V("x"), T0Mapp(V("f"), V("z"))))
        result = t0erm_subst0(term, "x", I(1))
        self.assertEqual(result, T0Mlam("y", T0Mpair(I(1), T0Mapp(V("f"), V("z")))))
        # fv cache shouldn't go stale
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "f", "z"}))
        self.assertEqual(t0erm_fvset(result), frozenset({"f", "z"}))
        untouched = T0Mlam("y", V("y"))
        self.assertIs(t0erm_subst0(untouched, "x", I(1)), untouched)

    def test_comparisons_produce_booleans(self):
        for op, l, r, expected in [("<", 1, 2, True), (">", 1, 2, False),
                                   (">=", 2, 2, True), ("==", 3, 3, True),
                                   ("!=", 3, 3, False)]:
            with self.subTest(op=op):
                self.assertEqual(ev(T0Mop2(op, I(l), I(r))), T0Mbtf(expected))


if __name__ == "__main__":
    unittest.main(verbosity=2)
