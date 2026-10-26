"""The shared evaluator.

Obligation 2 (left-to-right CBV, no reduction under lambdas, zero-step
values, determinism, budget exhaustion), ACC-02 .. ACC-04, and the source
path of the same evaluator (every source constructor, source errors).
"""
import ast
import copy
import unittest
from pathlib import Path

import helpers
from church import ADD, NUM
from evaluator import EXHAUSTED, VALUE, EvalError, _Machine, evaluate
from examples import FACT, LOOP
from source_syntax import (D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam,
                           D0Elet, D0Eop1, D0Eop2, D0Epair, D0Epfst, D0Epsnd,
                           D0Evar, source_value_to_python)
from target import App, Lam, Var, alpha_equiv
from compiler import compile_expr

I = Lam("x", Var("x"))
OMEGA_HALF = Lam("x", App(Var("x"), Var("x")))
OMEGA = App(OMEGA_HALF, OMEGA_HALF)


class TargetReductionTests(unittest.TestCase):
    def test_lambda_is_value_in_zero_steps(self):
        # ACC-02: lam x. ((lam y. y) x) is a value; its body is not reduced
        t = Lam("x", App(Lam("y", Var("y")), Var("x")))
        r = evaluate(t, 10)
        self.assertEqual((r.status, r.steps), (VALUE, 0))
        self.assertIs(r.value, t)

    def test_left_to_right_order(self):
        # ACC-02: (I1 I2) (I3 I4) contracts the left child, then the right
        # child, then the outer application.
        i1, i2, i3, i4 = (Lam(n, Var(n)) for n in "abcd")
        trace = []
        r = evaluate(App(App(i1, i2), App(i3, i4)), 10, trace=trace)
        self.assertEqual(r.steps, 3)
        self.assertEqual(trace, [(i1, i2), (i3, i4), (i2, i4)])
        self.assertEqual(r.value, i4)

    def test_argument_evaluated_before_substitution(self):
        # (lam x. lam y. x) (I I): the argument is reduced first (call by value)
        trace = []
        t = App(Lam("x", Lam("y", Var("x"))), App(I, I))
        r = evaluate(t, 10, trace=trace)
        self.assertEqual(r.steps, 2)
        self.assertEqual(trace[0], (I, I))
        self.assertEqual(r.value, Lam("y", I))

    def test_budget_boundaries(self):
        # ACC-03
        r = evaluate(I, 0)
        self.assertEqual((r.status, r.steps), (VALUE, 0))
        r = evaluate(App(I, I), 0)
        self.assertEqual((r.status, r.steps, r.value), (EXHAUSTED, 0, None))
        r = evaluate(App(I, I), 1)
        self.assertEqual((r.status, r.steps), (VALUE, 1))
        self.assertEqual(r.value, I)

    def test_value_on_last_step_completes(self):
        t = App(App(I, I), App(I, I))       # needs exactly 3 steps
        self.assertEqual(evaluate(t, 3).status, VALUE)
        r = evaluate(t, 2)
        self.assertEqual((r.status, r.steps), (EXHAUSTED, 2))

    def test_divergence_exhausts(self):
        r = evaluate(OMEGA, 1000)
        self.assertEqual((r.status, r.steps), (EXHAUSTED, 1000))

    def test_deterministic_and_input_preserved(self):
        # ACC-04
        t = compile_expr(D0Eapp(FACT(), D0Eint(3)))
        snapshot = copy.deepcopy(t)
        a = evaluate(t, helpers.EXEC)
        b = evaluate(t, helpers.EXEC)
        self.assertEqual((a.status, a.steps), (b.status, b.steps))
        self.assertEqual(a.value, b.value)
        self.assertEqual(t, snapshot)

    def test_open_terms_rejected(self):
        with self.assertRaises(EvalError):
            evaluate(App(Lam("x", Var("x")), Var("free")), 10)

    def test_bad_budget(self):
        for bad in (-1, 1.5, "3", True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                evaluate(I, bad)

    def test_no_church_shortcut(self):
        # ADD 2 3 is reduced by beta steps only; the value is a lambda with
        # unevaluated redexes inside, not a normalised numeral 5.
        r = evaluate(App(App(ADD, NUM(2)), NUM(3)), 100)
        self.assertEqual(r.steps, 2)
        self.assertFalse(alpha_equiv(r.value, NUM(5)))
        self.assertEqual(helpers.nat(r.value), 5)


class SourcePathTests(unittest.TestCase):
    """The same evaluator on source ASTs (expected results for comparison)."""

    def run_src(self, e):
        return source_value_to_python(evaluate(e).value)

    def test_literals_and_values(self):
        self.assertEqual(self.run_src(D0Eint(0)), 0)
        self.assertEqual(self.run_src(D0Ebtf(True)), True)
        self.assertEqual(self.run_src(D0Ebtf(False)), False)
        self.assertEqual(self.run_src(D0Elam("x", D0Evar("x"))), "<function>")
        self.assertEqual(self.run_src(D0Efix("f", "x", D0Evar("x"))), "<function>")

    def test_operators(self):
        cases = {"+": 7, "-": 3, "*": 10, "<": False, "<=": False, ">": True,
                 ">=": True, "==": False, "!=": True}
        for op, want in cases.items():
            with self.subTest(op=op):
                self.assertEqual(self.run_src(D0Eop2(op, D0Eint(5), D0Eint(2))), want)
        self.assertEqual(self.run_src(D0Eop2("-", D0Eint(2), D0Eint(5))), 0)

    def test_control_and_data(self):
        t, f = D0Ebtf(True), D0Ebtf(False)
        self.assertEqual(self.run_src(D0Eif0(f, D0Eint(1), D0Eint(2))), 2)
        self.assertEqual(self.run_src(D0Elet("x", D0Eint(4), D0Evar("x"))), 4)
        self.assertEqual(self.run_src(D0Epair(D0Eint(1), t)), (1, True))
        self.assertEqual(self.run_src(D0Epfst(D0Epair(D0Eint(1), t))), 1)
        self.assertEqual(self.run_src(D0Epsnd(D0Epair(D0Eint(1), t))), True)
        self.assertEqual(self.run_src(D0Eop1("not", f)), True)
        self.assertEqual(self.run_src(D0Eop2("and", f, LOOP())), False)
        self.assertEqual(self.run_src(D0Eop2("or", t, LOOP())), True)
        self.assertEqual(self.run_src(D0Eapp(FACT(), D0Eint(5))), 120)

    def test_coincident_fix_binders(self):
        self.assertEqual(self.run_src(D0Eapp(D0Efix("f", "f", D0Evar("f")), D0Eint(3))), 3)

    def test_source_errors(self):
        bad = [D0Evar("nope"),
               D0Eop2("+", D0Eint(1), D0Ebtf(True)),
               D0Eif0(D0Eint(1), D0Eint(1), D0Eint(2)),
               D0Epfst(D0Eint(1)),
               D0Eapp(D0Eint(1), D0Eint(2)),
               D0Eop2("/", D0Eint(4), D0Eint(2)),
               D0Eint(-1)]
        for e in bad:
            with self.subTest(e=e), self.assertRaises(EvalError):
                evaluate(e)

    def test_source_budget_counts_beta_steps(self):
        r = evaluate(LOOP(), 500)
        self.assertEqual((r.status, r.steps), (EXHAUSTED, 500))


class SharedEvaluatorStructureTests(unittest.TestCase):
    def test_same_methods_handle_both_languages(self):
        # Var/Lam/App and D0Evar/D0Elam/D0Eapp dispatch to the same methods.
        calls = []
        orig = _Machine.visit_app

        def spy(self, node):
            calls.append(type(node).__name__)
            return orig(self, node)

        _Machine.visit_app = spy
        try:
            evaluate(App(I, I), 5)
            evaluate(D0Eapp(D0Elam("x", D0Evar("x")), D0Eint(1)))
        finally:
            _Machine.visit_app = orig
        self.assertEqual(calls, ["App", "D0Eapp"])

    def test_evaluator_does_not_import_compiler(self):
        src = (helpers.SOLUTION / "evaluator.py").read_text(encoding="utf-8")
        imported = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom):
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
        self.assertNotIn("compiler", imported)
        self.assertNotIn("church", imported)


if __name__ == "__main__":
    unittest.main()
