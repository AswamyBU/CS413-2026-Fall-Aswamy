"""unittest suite for PrettyPrintVisitor and SubstitutionVisitor.

Run from assigns/05:
    python -m unittest discover -s MySolution/TEST -p "test_unittest_*.py" -v
"""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lambda1_visitors import (  # noqa: E402
    PrettyPrintVisitor, SubstitutionVisitor, FreshNames,
    d0exp_pretty, d0exp_substitute, d0exp_names,
)
import lambda1_vp as L  # noqa: E402  (lambda1_visitors puts it on sys.path)
from lambda1_vp import (  # noqa: E402
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar, D0Elam, D0Efix,
    D0Eapp, D0Eif0, D0Elet, D0Epair, D0Epfst, D0Epsnd, d0exp_fvset,
)

V, I = D0Evar, D0Eint


def add(a, b):
    return D0Eop2("+", a, b)


P = d0exp_pretty


def S(e, x, r):
    return P(d0exp_substitute(e, x, r))


class PrettyPrintTests(unittest.TestCase):
    def test_every_constructor(self):
        cases = [
            (I(42), "42"),
            (D0Ebtf(True), "true"),
            (D0Ebtf(False), "false"),
            (V("x"), "x"),
            (D0Eop1("-", I(3)), "(- 3)"),
            (D0Eop2("<=", V("a"), I(1)), "(a <= 1)"),
            (D0Elam("x", V("x")), "(lam x. x)"),
            (D0Efix("f", "n", D0Eapp(V("f"), V("n"))), "(fix f(n). (f n))"),
            (D0Eapp(V("f"), I(1)), "(f 1)"),
            (D0Eif0(D0Ebtf(True), I(1), I(2)), "(if true then 1 else 2)"),
            (D0Elet("x", I(1), V("x")), "(let x = 1 in x)"),
            (D0Epair(I(1), D0Ebtf(False)), "(pair 1 false)"),
            (D0Epfst(V("p")), "(fst p)"),
            (D0Epsnd(V("p")), "(snd p)"),
        ]
        for e, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(P(e), expected)
                self.assertEqual(e.accept(PrettyPrintVisitor()), expected)

    def test_integers(self):
        self.assertEqual(P(I(0)), "0")
        self.assertEqual(P(I(-17)), "-17")
        self.assertEqual(P(I(10 ** 30)), "1" + "0" * 30)
        self.assertEqual(P(I(-(2 ** 100))), str(-(2 ** 100)))

    def test_assignment_example(self):
        e = D0Eapp(D0Elam("x", D0Eop2("+", V("x"), I(1))), I(4))
        self.assertEqual(P(e), "((lam x. (x + 1)) 4)")

    def test_nested(self):
        fact = D0Efix("f", "n", D0Eif0(
            D0Eop2("<=", V("n"), I(0)), I(1),
            D0Eop2("*", V("n"), D0Eapp(V("f"), D0Eop2("-", V("n"), I(1))))))
        e = D0Elet("p", D0Epair(D0Eapp(fact, I(5)), D0Eop1("not", D0Ebtf(True))),
                   D0Epair(D0Epsnd(V("p")), D0Epfst(V("p"))))
        self.assertEqual(
            P(e),
            "(let p = (pair ((fix f(n). (if (n <= 0) then 1 else (n * (f (n - 1))))) 5)"
            " (not true)) in (pair (snd p) (fst p)))")

    def test_no_evaluation(self):
        self.assertEqual(P(D0Eop2("/", I(1), I(0))), "(1 / 0)")
        omega = D0Eapp(D0Efix("f", "x", D0Eapp(V("f"), V("x"))), I(0))
        self.assertEqual(P(omega), "((fix f(x). (f x)) 0)")
        self.assertEqual(P(D0Eop2("+", D0Ebtf(True), I(1))), "(true + 1)")

    def test_no_surrounding_whitespace(self):
        s = P(D0Elam("x", V("x")))
        self.assertEqual(s, s.strip())
        self.assertNotIn("\n", s)


class SubstitutionBasicsTests(unittest.TestCase):
    def test_assignment_examples(self):
        y, f = V("y"), V("f")
        cases = [
            (add(V("x"), V("z")), "x", I(3), "(3 + z)"),
            (D0Elam("x", add(V("x"), y)), "x", I(3), "(lam x. (x + y))"),
            (D0Elam("y", add(V("x"), y)), "x", y, "(lam y_1. (y + y_1))"),
            (D0Elet("x", V("x"), add(V("x"), y)), "x", I(3), "(let x = 3 in (x + y))"),
            (D0Elet("y", V("x"), add(V("x"), y)), "x", y, "(let y_1 = y in (y + y_1))"),
            (D0Efix("f", "n", add(V("x"), D0Eapp(f, V("n")))), "x", f,
             "(fix f_1(n). (f + (f_1 n)))"),
            (V("x"), "x", add(V("x"), I(1)), "(x + 1)"),
        ]
        for e, x, r, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(S(e, x, r), expected)

    def test_every_constructor(self):
        r = add(V("a"), I(1))
        x = V("x")
        cases = [
            (I(7), "7"),
            (D0Ebtf(True), "true"),
            (D0Ebtf(False), "false"),
            (x, "(a + 1)"),
            (V("z"), "z"),
            (D0Eop1("-", x), "(- (a + 1))"),
            (D0Eop2("*", x, V("z")), "((a + 1) * z)"),
            (D0Elam("z", x), "(lam z. (a + 1))"),
            (D0Efix("g", "z", D0Eapp(V("g"), x)), "(fix g(z). (g (a + 1)))"),
            (D0Eapp(x, x), "((a + 1) (a + 1))"),
            (D0Eif0(x, x, V("w")), "(if (a + 1) then (a + 1) else w)"),
            (D0Elet("z", x, x), "(let z = (a + 1) in (a + 1))"),
            (D0Epair(x, I(2)), "(pair (a + 1) 2)"),
            (D0Epfst(x), "(fst (a + 1))"),
            (D0Epsnd(x), "(snd (a + 1))"),
        ]
        for e, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(S(e, "x", r), expected)
                # Direct visitor use gives the same result as the entry point.
                direct = e.accept(SubstitutionVisitor({"x": r}, FreshNames({"x", "a"})))
                self.assertEqual(P(direct), expected)

    def test_operators_preserved(self):
        for op in ["+", "-", "*", "/", "<", "<=", "=", "!="]:
            out = d0exp_substitute(D0Eop2(op, V("x"), V("x")), "x", I(2))
            self.assertEqual(out, D0Eop2(op, I(2), I(2)))
        self.assertEqual(d0exp_substitute(D0Eop1("not", V("x")), "x", D0Ebtf(True)),
                         D0Eop1("not", D0Ebtf(True)))

    def test_replacement_contains_target(self):
        self.assertEqual(S(add(V("x"), V("x")), "x", add(V("x"), I(1))),
                         "((x + 1) + (x + 1))")
        # Single substitution: the inserted x is not substituted again.
        self.assertEqual(S(D0Elam("y", V("x")), "x", D0Eapp(V("x"), V("x"))),
                         "(lam y. (x x))")

    def test_nonmatching_variable(self):
        e = D0Elam("y", add(V("y"), V("z")))
        self.assertEqual(d0exp_substitute(e, "x", V("y")), e)

    def test_replacement_inserted_unchanged(self):
        r = D0Epair(I(1), I(2))
        out = d0exp_substitute(V("x"), "x", r)
        self.assertEqual(out, r)


class ShadowingTests(unittest.TestCase):
    def test_lambda_shadows(self):
        e = D0Epair(V("x"), D0Elam("x", V("x")))
        self.assertEqual(S(e, "x", I(9)), "(pair 9 (lam x. x))")

    def test_fix_function_name_shadows(self):
        e = D0Epair(V("f"), D0Efix("f", "n", D0Eapp(V("f"), V("n"))))
        self.assertEqual(S(e, "f", I(9)), "(pair 9 (fix f(n). (f n)))")

    def test_fix_parameter_shadows(self):
        e = D0Efix("f", "n", add(V("n"), V("m")))
        self.assertEqual(S(e, "n", I(9)), "(fix f(n). (n + m))")

    def test_fix_same_name_for_function_and_parameter(self):
        e = D0Efix("n", "n", add(V("n"), V("x")))
        self.assertEqual(S(e, "n", I(9)), "(fix n(n). (n + x))")
        # Capture: both binders become the same fresh name, so the parameter
        # still shadows the function name.
        out = d0exp_substitute(e, "x", V("n"))
        self.assertEqual(P(out), "(fix n_1(n_1). (n_1 + n))")
        self.assertEqual(out.arg1, out.arg2)

    def test_let_shadows_only_body(self):
        e = D0Elet("x", add(V("x"), I(1)), V("x"))
        self.assertEqual(S(e, "x", I(5)), "(let x = (5 + 1) in x)")

    def test_inner_rebinding_stops_substitution(self):
        e = D0Elam("y", D0Eapp(V("x"), D0Elam("x", V("x"))))
        self.assertEqual(S(e, "x", I(1)), "(lam y. (1 (lam x. x)))")


class CaptureAvoidanceTests(unittest.TestCase):
    def test_lambda_capture(self):
        e = D0Elam("y", add(V("x"), V("y")))
        out = d0exp_substitute(e, "x", V("y"))
        self.assertEqual(P(out), "(lam y_1. (y + y_1))")
        self.assertNotEqual(P(out), "(lam y. (y + y))")

    def test_let_capture(self):
        e = D0Elet("y", I(1), add(V("x"), V("y")))
        self.assertEqual(S(e, "x", V("y")), "(let y_1 = 1 in (y + y_1))")

    def test_fix_function_name_capture(self):
        e = D0Efix("f", "n", add(V("x"), D0Eapp(V("f"), V("n"))))
        self.assertEqual(S(e, "x", V("f")), "(fix f_1(n). (f + (f_1 n)))")

    def test_fix_parameter_capture(self):
        e = D0Efix("f", "n", add(V("x"), D0Eapp(V("f"), V("n"))))
        self.assertEqual(S(e, "x", V("n")), "(fix f(n_1). (n + (f n_1)))")

    def test_fix_both_binders_capture(self):
        e = D0Efix("f", "n", add(V("x"), D0Eapp(V("f"), V("n"))))
        self.assertEqual(S(e, "x", D0Eapp(V("f"), V("n"))),
                         "(fix f_1(n_1). ((f n) + (f_1 n_1)))")

    def test_no_unnecessary_renaming(self):
        # x not free under the binder: y is left alone even though r mentions y.
        self.assertEqual(S(D0Elam("y", V("y")), "x", V("y")), "(lam y. y)")
        self.assertEqual(S(D0Elam("x", V("y")), "x", V("y")), "(lam x. y)")
        self.assertEqual(S(D0Efix("f", "n", V("n")), "x", V("f")), "(fix f(n). n)")
        # Only the conflicting binder is renamed.
        e = D0Efix("f", "n", add(V("x"), D0Eapp(V("f"), V("n"))))
        self.assertEqual(S(e, "x", V("z")), "(fix f(n). (z + (f n)))")


class RenamingScopeTests(unittest.TestCase):
    def test_nested_shadowing_during_renaming(self):
        # Inner lam y rebinds y; its y must stay bound to the inner binder.
        e = D0Elam("y", add(V("x"), D0Eapp(D0Elam("y", add(V("x"), V("y"))), V("y"))))
        self.assertEqual(S(e, "x", V("y")),
                         "(lam y_1. (y + ((lam y_2. (y + y_2)) y_1)))")

    def test_inner_shadow_without_target_keeps_name(self):
        e = D0Elam("y", D0Eapp(D0Elam("y", V("y")), add(V("x"), V("y"))))
        self.assertEqual(S(e, "x", V("y")),
                         "(lam y_1. ((lam y. y) (y + y_1)))")

    def test_fresh_name_avoids_existing_bound_name(self):
        e = D0Elam("y", D0Elam("y_1", add(V("x"), add(V("y"), V("y_1")))))
        self.assertEqual(S(e, "x", V("y")),
                         "(lam y_2. (lam y_1. (y + (y_2 + y_1))))")

    def test_fresh_name_avoids_names_in_replacement_and_free_names(self):
        e = D0Elam("y", add(V("x"), add(V("y"), V("y_1"))))
        self.assertEqual(S(e, "x", add(V("y"), V("y_2"))),
                         "(lam y_3. ((y + y_2) + (y_3 + y_1)))")

    def test_fresh_name_avoids_names_generated_earlier(self):
        e = D0Epair(D0Elam("y", add(V("x"), V("y"))), D0Elam("y", add(V("x"), V("y"))))
        self.assertEqual(S(e, "x", V("y")),
                         "(pair (lam y_1. (y + y_1)) (lam y_2. (y + y_2)))")

    def test_fresh_names_supply(self):
        fresh = FreshNames({"a", "a_1", "a_3"})
        self.assertEqual([fresh.fresh("a"), fresh.fresh("a"), fresh.fresh("a")],
                         ["a_2", "a_4", "a_5"])

    def test_target_name_is_avoided(self):
        # x_1 must not be generated if it would equal the target.
        e = D0Elam("x", D0Elam("y", add(V("x_1"), V("y"))))
        self.assertEqual(S(e, "x_1", V("x")), "(lam x_2. (lam y. (x + y)))")

    def test_names_visitor(self):
        e = D0Elet("a", V("b"), D0Efix("c", "d", D0Elam("e", V("f"))))
        self.assertEqual(d0exp_names(e), frozenset("abcdef"))


class LetInitializerTests(unittest.TestCase):
    def test_initializer_substituted_even_if_name_is_target(self):
        e = D0Elet("x", V("x"), V("x"))
        self.assertEqual(S(e, "x", I(3)), "(let x = 3 in x)")

    def test_initializer_not_renamed(self):
        # The binder y is renamed in the body only; the y in init stays put
        # because it refers to an outer y.
        e = D0Elet("y", add(V("y"), V("x")), add(V("x"), V("y")))
        self.assertEqual(S(e, "x", V("y")), "(let y_1 = (y + y) in (y + y_1))")

    def test_let_binds_only_body(self):
        e = D0Elet("y", V("x"), V("y"))
        # x is not free in the body, so no renaming is needed.
        self.assertEqual(S(e, "x", V("y")), "(let y = y in y)")


class PreservationAndDeterminismTests(unittest.TestCase):
    def test_inputs_not_mutated(self):
        e = D0Elam("y", D0Elet("y", V("x"), D0Efix("f", "n", add(V("x"), V("f")))))
        r = D0Eapp(V("y"), V("f"))
        e0, r0 = copy.deepcopy(e), copy.deepcopy(r)
        d0exp_substitute(e, "x", r)
        d0exp_pretty(e)
        self.assertEqual(e, e0)
        self.assertEqual(r, r0)
        self.assertEqual(P(e), P(e0))

    def test_deterministic(self):
        e = D0Efix("f", "n", D0Elam("y", add(V("x"), D0Eapp(V("f"), V("y")))))
        r = D0Epair(V("f"), V("y"))
        outs = {P(d0exp_substitute(e, "x", r)) for _ in range(5)}
        self.assertEqual(outs, {"(fix f_1(n). (lam y_1. ((pair f y) + (f_1 y_1))))"})

    def test_no_evaluation_during_substitution(self):
        def boom(*args, **kwargs):
            raise AssertionError("evaluation attempted")
        omega = D0Eapp(D0Efix("f", "z", D0Eapp(V("f"), V("z"))), V("x"))
        e = D0Epair(D0Eop2("/", V("x"), I(0)), omega)
        with mock.patch.object(L, "d0exp_evaluate", boom), \
                mock.patch.object(L.EvaluateVisitor, "visit_app", boom), \
                mock.patch.object(L.EvaluateVisitor, "visit_op2", boom):
            out = d0exp_substitute(e, "x", I(1))
            text = P(out)
        self.assertEqual(text, "(pair (1 / 0) ((fix f(z). (f z)) 1))")


class FreeVariablePropertyTests(unittest.TestCase):
    EXAMPLES = [
        (add(V("x"), V("z")), "x", I(3)),
        (D0Elam("y", add(V("x"), V("y"))), "x", V("y")),
        (D0Elet("y", V("x"), add(V("x"), V("y"))), "x", V("y")),
        (D0Efix("f", "n", add(V("x"), D0Eapp(V("f"), V("n")))), "x", D0Eapp(V("f"), V("n"))),
        (D0Efix("n", "n", add(V("x"), V("n"))), "x", V("n")),
        (V("x"), "x", add(V("x"), V("q"))),
        (D0Elam("y", D0Eapp(D0Elam("y", V("x")), V("y"))), "x", D0Epair(V("y"), V("w"))),
    ]

    NOT_FREE = [
        (D0Elam("x", add(V("x"), V("y"))), "x", V("y")),
        (D0Elet("x", I(1), V("x")), "x", V("z")),
        (D0Efix("x", "n", V("x")), "x", V("n")),
        (D0Efix("f", "x", V("x")), "x", V("f")),
        (add(V("a"), V("b")), "x", V("a")),
    ]

    def test_fv_property_when_free(self):
        for e, x, r in self.EXAMPLES:
            with self.subTest(e=P(e)):
                self.assertIn(x, d0exp_fvset(e))
                out = d0exp_substitute(e, x, r)
                self.assertEqual(d0exp_fvset(out),
                                 (d0exp_fvset(e) - {x}) | d0exp_fvset(r))

    def test_unchanged_when_not_free(self):
        for e, x, r in self.NOT_FREE:
            with self.subTest(e=P(e)):
                self.assertNotIn(x, d0exp_fvset(e))
                out = d0exp_substitute(e, x, r)
                self.assertEqual(out, e)
                self.assertEqual(d0exp_fvset(out), d0exp_fvset(e))


if __name__ == "__main__":
    unittest.main()
