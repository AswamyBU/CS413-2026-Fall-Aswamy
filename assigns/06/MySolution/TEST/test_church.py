"""Church-encoding library, tested directly on target terms (ACC-05).

Every combinator is closed and pure. Arithmetic, comparisons, and boolean
operators are checked with explicit expected answers, including predecessor
of zero, equal and unequal operands, both outcomes of every comparison, and
full truth tables.
"""
import itertools
import unittest

from helpers import boolean, nat
from church import (ADD, AND, EQ, FALSE, FST, GEQ, GT, I, IS_ZERO, LEQ,
                    LIBRARY, LT, MUL, NEQ, NOT, NUM, OR, PAIR, PRED, SND, SUB,
                    SUCC, TRUE, Z, apps, lams)
from evaluator import EXHAUSTED, evaluate
from target import App, Lam, Var, alpha_equiv, is_pure, show

v = Var


class LibraryShapeTests(unittest.TestCase):
    def test_all_combinators_closed_and_pure(self):
        for name, term in LIBRARY.items():
            with self.subTest(name=name):
                self.assertEqual(term.fv, frozenset())
                self.assertTrue(is_pure(term))

    def test_required_shapes(self):
        self.assertEqual(show(TRUE), "(lam t. (lam f. t))")
        self.assertEqual(show(FALSE), "(lam t. (lam f. f))")
        self.assertEqual(show(NUM(0)), "(lam s. (lam z. z))")
        self.assertEqual(show(NUM(2)), "(lam s. (lam z. (s (s z))))")
        self.assertEqual(show(PAIR), "(lam a. (lam b. (lam p. ((p a) b))))")
        self.assertEqual(
            show(Z), "(lam g. ((lam x. (g (lam v. ((x x) v)))) (lam x. (g (lam v. ((x x) v))))))")

    def test_zero_and_false_are_alpha_equivalent(self):
        self.assertTrue(alpha_equiv(NUM(0), FALSE))

    def test_num_rejects_negative(self):
        with self.assertRaises(ValueError):
            NUM(-1)


class ArithmeticTests(unittest.TestCase):
    def test_numerals(self):
        for n in range(6):
            self.assertEqual(nat(NUM(n)), n)

    def test_succ(self):
        for n in range(4):
            self.assertEqual(nat(App(SUCC, NUM(n))), n + 1)

    def test_pred_including_zero(self):
        self.assertEqual(nat(App(PRED, NUM(0))), 0)
        for n in range(1, 5):
            self.assertEqual(nat(App(PRED, NUM(n))), n - 1)

    def test_is_zero(self):
        self.assertIs(boolean(App(IS_ZERO, NUM(0))), True)
        self.assertIs(boolean(App(IS_ZERO, NUM(1))), False)
        self.assertIs(boolean(App(IS_ZERO, NUM(3))), False)

    def test_add_sub_mul(self):
        for m, n in itertools.product(range(4), repeat=2):
            with self.subTest(m=m, n=n):
                self.assertEqual(nat(apps(ADD, NUM(m), NUM(n))), m + n)
                self.assertEqual(nat(apps(SUB, NUM(m), NUM(n))), max(m - n, 0))
                self.assertEqual(nat(apps(MUL, NUM(m), NUM(n))), m * n)

    def test_truncated_subtraction(self):
        self.assertEqual(nat(apps(SUB, NUM(2), NUM(5))), 0)
        self.assertEqual(nat(apps(SUB, NUM(5), NUM(2))), 3)
        self.assertEqual(nat(apps(SUB, NUM(3), NUM(3))), 0)


class ComparisonTests(unittest.TestCase):
    # (less, equal, greater) operand pairs give both outcomes of every test.
    PAIRS = [(1, 3), (2, 2), (4, 1), (0, 0), (0, 2), (3, 0)]
    OPS = {"<": (LT, lambda a, b: a < b), "<=": (LEQ, lambda a, b: a <= b),
           ">": (GT, lambda a, b: a > b), ">=": (GEQ, lambda a, b: a >= b),
           "==": (EQ, lambda a, b: a == b), "!=": (NEQ, lambda a, b: a != b)}

    def test_every_comparison(self):
        for name, (term, py) in self.OPS.items():
            outcomes = set()
            for m, n in self.PAIRS:
                with self.subTest(op=name, m=m, n=n):
                    got = boolean(apps(term, NUM(m), NUM(n)))
                    self.assertIs(got, py(m, n))
                    outcomes.add(got)
            self.assertEqual(outcomes, {True, False}, name)


class BooleanAndPairTests(unittest.TestCase):
    def test_not(self):
        self.assertIs(boolean(App(NOT, TRUE)), False)
        self.assertIs(boolean(App(NOT, FALSE)), True)

    def test_and_or_truth_tables(self):
        enc = {True: TRUE, False: FALSE}
        for a, b in itertools.product([True, False], repeat=2):
            with self.subTest(a=a, b=b):
                self.assertIs(boolean(apps(AND, enc[a], enc[b])), a and b)
                self.assertIs(boolean(apps(OR, enc[a], enc[b])), a or b)

    def test_pair_projections(self):
        p = apps(PAIR, NUM(2), TRUE)
        self.assertEqual(nat(App(FST, p)), 2)
        self.assertIs(boolean(App(SND, p)), True)

    def test_identity(self):
        self.assertEqual(nat(App(I, NUM(3))), 3)


class FixedPointTests(unittest.TestCase):
    def sum_to(self):
        # Z (lam f. lam n. (IS_ZERO n (lam u. 0) (lam u. n + f (PRED n))) I)
        body = App(apps(App(IS_ZERO, v("n")),
                        lams("u", NUM(0)),
                        lams("u", apps(ADD, v("n"), App(v("f"), App(PRED, v("n")))))),
                   I)
        return App(Z, lams("f", "n", body))

    def test_z_recursion(self):
        self.assertEqual(nat(App(self.sum_to(), NUM(4))), 10)
        self.assertEqual(nat(App(self.sum_to(), NUM(0))), 0)

    def test_z_application_is_a_value_quickly(self):
        r = evaluate(self.sum_to(), 10)
        self.assertTrue(r.completed)
        self.assertIsInstance(r.value, Lam)

    def test_ordinary_y_diverges_under_cbv(self):
        half = lams("x", App(v("g"), App(v("x"), v("x"))))
        Y = lams("g", App(half, half))
        r = evaluate(App(Y, lams("f", "n", v("n"))), 2000)
        self.assertEqual(r.status, EXHAUSTED)


if __name__ == "__main__":
    unittest.main()
