"""Target AST: printer, free variables, substitution, alpha-equivalence.

Obligation 1 (substitution with shadowing and capture hazards) and ACC-01,
ACC-13. Everything here is tested on open terms, without any evaluation.
"""
import copy
import unittest

import helpers  # noqa: F401  (sets sys.path)
from target import (App, Lam, Var, all_names, alpha_equiv, fresh_name,
                    free_vars, is_pure, show, substitute)

x, y, z = Var("x"), Var("y"), Var("z")


class PrinterTests(unittest.TestCase):
    def test_variable(self):
        self.assertEqual(show(Var("x")), "x")

    def test_abstraction(self):
        self.assertEqual(show(Lam("x", x)), "(lam x. x)")

    def test_application(self):
        self.assertEqual(show(App(x, y)), "(x y)")

    def test_nested(self):
        t = App(Lam("x", App(x, Lam("y", App(y, x)))), Lam("z", z))
        self.assertEqual(show(t), "((lam x. (x (lam y. (y x)))) (lam z. z))")

    def test_long_spine_does_not_overflow(self):
        t = z
        for _ in range(5000):
            t = App(Var("s"), t)
        self.assertTrue(show(t).startswith("(s (s "))


class FreeVariableTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(free_vars(x), {"x"})
        self.assertEqual(free_vars(Lam("x", x)), set())
        self.assertEqual(free_vars(Lam("x", App(x, y))), {"y"})
        self.assertEqual(free_vars(App(Lam("x", x), x)), {"x"})

    def test_shadowing(self):
        t = Lam("x", App(Lam("x", x), y))
        self.assertEqual(free_vars(t), {"y"})

    def test_all_names_includes_binders(self):
        self.assertEqual(all_names(Lam("a", App(Var("b"), Var("a")))), {"a", "b"})


class SubstitutionTests(unittest.TestCase):
    def test_acc01_capture_hazard(self):
        # (lam y. x)[x := y]  must be  lam fresh. y  with y still free
        result = substitute(Lam("y", x), "x", y)
        self.assertIsInstance(result, Lam)
        self.assertNotEqual(result.param, "y")
        self.assertEqual(result.body, y)
        self.assertTrue(alpha_equiv(result, Lam("fresh", y)))
        self.assertEqual(free_vars(result), {"y"})

    def test_rename_policy_is_deterministic(self):
        t = Lam("y", App(x, y))
        a = substitute(t, "x", y)
        b = substitute(t, "x", y)
        self.assertEqual(a, b)
        self.assertEqual(show(a), "(lam y_1. (y y_1))")

    def test_fresh_name_skips_existing_names(self):
        t = Lam("y", App(App(x, y), Var("y_1")))
        result = substitute(t, "x", y)
        self.assertEqual(show(result), "(lam y_2. ((y y_2) y_1))")

    def test_shadowing_binder_blocks_substitution(self):
        t = Lam("x", x)
        self.assertIs(substitute(t, "x", y), t)

    def test_inner_shadowing(self):
        # (lam z. x (lam x. x))[x := y]  =  lam z. y (lam x. x)
        t = Lam("z", App(x, Lam("x", x)))
        self.assertEqual(substitute(t, "x", y), Lam("z", App(y, Lam("x", x))))

    def test_no_needless_renaming(self):
        # y is a binder but x is not free under it: nothing to rename
        t = App(x, Lam("y", y))
        self.assertEqual(substitute(t, "x", y), App(y, Lam("y", y)))

    def test_nested_capture(self):
        # (lam y. lam z. x y z)[x := y z]
        t = Lam("y", Lam("z", App(App(x, y), z)))
        r = App(y, z)
        result = substitute(t, "x", r)
        self.assertEqual(free_vars(result), {"y", "z"})
        expected = Lam("a", Lam("b", App(App(App(y, z), Var("a")), Var("b"))))
        self.assertTrue(alpha_equiv(result, expected))

    def test_free_variable_law(self):
        cases = [
            (Lam("y", App(x, y)), "x", App(y, z)),
            (App(Lam("x", x), x), "x", Lam("q", y)),
            (Lam("z", Lam("y", App(x, App(y, z)))), "x", App(z, y)),
        ]
        for t, name, r in cases:
            with self.subTest(t=show(t)):
                result = substitute(t, name, r)
                want = (free_vars(t) - {name}) | free_vars(r)
                self.assertEqual(free_vars(result), want)

    def test_inputs_not_mutated(self):
        t = Lam("y", App(x, Lam("x", App(x, y))))
        r = App(y, Lam("q", x))
        t0, r0 = copy.deepcopy(t), copy.deepcopy(r)
        substitute(t, "x", r)
        self.assertEqual(t, t0)
        self.assertEqual(r, r0)

    def test_replacement_preserved(self):
        r = Lam("w", App(Var("w"), y))
        result = substitute(App(x, x), "x", r)
        self.assertEqual(result, App(r, r))


class AlphaAndPurityTests(unittest.TestCase):
    def test_alpha_equiv(self):
        self.assertTrue(alpha_equiv(Lam("a", Var("a")), Lam("b", Var("b"))))
        self.assertFalse(alpha_equiv(Lam("a", Var("a")), Lam("b", Var("a"))))
        self.assertFalse(alpha_equiv(Var("a"), Var("b")))
        self.assertTrue(alpha_equiv(Lam("a", Lam("b", Var("a"))),
                                    Lam("b", Lam("a", Var("b")))))
        self.assertFalse(alpha_equiv(Lam("a", Lam("a", Var("a"))),
                                     Lam("a", Lam("b", Var("a")))))

    def test_is_pure(self):
        self.assertTrue(is_pure(App(Lam("x", x), y)))
        self.assertFalse(is_pure(App(Lam("x", x), "y")))
        self.assertFalse(is_pure(Var("1bad")))

    def test_fresh_name(self):
        self.assertEqual(fresh_name("u", {"x"}), "u")
        self.assertEqual(fresh_name("u", {"u", "u_1"}), "u_2")


if __name__ == "__main__":
    unittest.main()
