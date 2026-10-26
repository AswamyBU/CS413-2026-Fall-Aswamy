"""The compiler.

Obligations 3 (every constructor and operator), 4 (scope, fix binders,
open expressions, encoding-name collisions, FV preservation, immutability),
6 (rejection of unsupported forms), and 7 (purity, no evaluator calls).
Covers ACC-06, ACC-07, ACC-09, ACC-10. Each end-to-end check compares the
decoded target answer with an explicit expected value *and* with the
shared evaluator's result on the source AST.
"""
import copy
import itertools
import random
import unittest
from unittest import mock

import helpers
from helpers import BOOL, NAT, compiled_answer, source_result
import evaluator
from church import FALSE, FST, I, NUM, PAIR, SND, TRUE, Z, apps
from compiler import CompileError, compile_expr
from examples import FACT, FIB, LOOP
from source_syntax import (D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam,
                           D0Elet, D0Eop1, D0Eop2, D0Epair, D0Epfst, D0Epsnd,
                           D0Evar, d0exp_fvset)
from target import App, Lam, Var, alpha_equiv, is_pure, show

T, F = D0Ebtf(True), D0Ebtf(False)
n = D0Eint
x = D0Evar


def op(name, a, b):
    return D0Eop2(name, a, b)


class EndToEnd(unittest.TestCase):
    def check(self, source, kind, expected):
        """Target answer == expected == shared evaluator on the source."""
        self.assertEqual(source_result(source), expected, "source evaluator")
        got = compiled_answer(source, kind)
        self.assertEqual(got, expected, "compiled program")
        self.assertIs(type(got), type(expected))


class ConstructorTests(EndToEnd):
    def test_literals(self):
        self.check(n(0), NAT, 0)
        self.check(n(5), NAT, 5)
        self.check(T, BOOL, True)
        self.check(F, BOOL, False)

    def test_lambda_application_variable(self):
        self.check(D0Eapp(D0Elam("y", x("y")), n(3)), NAT, 3)
        self.check(D0Eapp(D0Eapp(D0Elam("a", D0Elam("b", x("a"))), n(1)), n(2)), NAT, 1)

    def test_let(self):
        self.check(D0Elet("a", n(2), op("*", x("a"), x("a"))), NAT, 4)

    def test_if_both_outcomes(self):
        self.check(D0Eif0(T, n(1), n(2)), NAT, 1)
        self.check(D0Eif0(F, n(1), n(2)), NAT, 2)

    def test_pairs(self):
        p = D0Epair(n(4), F)
        self.check(D0Epfst(p), NAT, 4)
        self.check(D0Epsnd(p), BOOL, False)

    def test_fix(self):
        self.check(D0Eapp(FACT(), n(0)), NAT, 1)
        self.check(D0Eapp(FACT(), n(3)), NAT, 6)
        self.check(D0Eapp(FIB(), n(6)), NAT, 8)

    def test_not(self):
        self.check(D0Eop1("not", T), BOOL, False)
        self.check(D0Eop1("not", F), BOOL, True)


class OperatorTests(EndToEnd):
    def test_arithmetic(self):
        self.check(op("+", n(0), n(0)), NAT, 0)
        self.check(op("+", n(2), n(3)), NAT, 5)
        self.check(op("-", n(5), n(2)), NAT, 3)
        self.check(op("-", n(2), n(5)), NAT, 0)
        self.check(op("-", n(3), n(3)), NAT, 0)
        self.check(op("-", op("-", n(0), n(1)), n(0)), NAT, 0)   # pred of zero
        self.check(op("*", n(3), n(4)), NAT, 12)
        self.check(op("*", n(0), n(4)), NAT, 0)

    def test_comparisons_both_outcomes_equal_and_unequal(self):
        py = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
              ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
              "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
        for name, fn in py.items():
            seen = set()
            for a, b in [(1, 3), (3, 3), (3, 1), (0, 0)]:
                with self.subTest(op=name, a=a, b=b):
                    self.check(op(name, n(a), n(b)), BOOL, fn(a, b))
                    seen.add(fn(a, b))
            self.assertEqual(seen, {True, False})

    def test_and_or_truth_tables(self):
        lit = {True: T, False: F}
        for a, b in itertools.product([True, False], repeat=2):
            with self.subTest(a=a, b=b):
                self.check(op("and", lit[a], lit[b]), BOOL, a and b)
                self.check(op("or", lit[a], lit[b]), BOOL, a or b)


class ScopeTests(EndToEnd):
    def test_nested_lets_and_shadowing(self):
        # let x = 1 in let y = x + 1 in let x = y * 3 in x + y  ==> 8
        e = D0Elet("x", n(1), D0Elet("y", op("+", x("x"), n(1)),
                   D0Elet("x", op("*", x("y"), n(3)), op("+", x("x"), x("y")))))
        self.check(e, NAT, 8)

    def test_let_initializer_scope(self):
        # let x = 1 in let x = x + 1 in x  ==> 2 (inner initializer sees outer x)
        e = D0Elet("x", n(1), D0Elet("x", op("+", x("x"), n(1)), x("x")))
        self.check(e, NAT, 2)

    def test_let_x_equals_x_is_open(self):
        # ACC-06: in `let x = x in x` the initializer's x is free
        e = D0Elet("x", x("x"), x("x"))
        t = compile_expr(e)
        self.assertEqual(t, App(Lam("x", Var("x")), Var("x")))
        self.assertEqual(t.fv, {"x"})

    def test_nested_lambda_shadowing(self):
        e = D0Eapp(D0Eapp(D0Elam("x", D0Elam("x", op("+", x("x"), n(1)))), n(10)), n(2))
        self.check(e, NAT, 3)

    def test_higher_order(self):
        twice = D0Elam("f", D0Elam("x", D0Eapp(x("f"), D0Eapp(x("f"), x("x")))))
        e = D0Eapp(D0Eapp(twice, D0Elam("y", op("*", x("y"), n(2)))), n(3))
        self.check(e, NAT, 12)

    def test_source_names_like_encoding_names(self):
        # s, z, t, f, m, n, p, a, b, g, v, w, q are all binder names inside
        # library combinators; source programs may use them freely.
        for name in ["s", "z", "t", "f", "m", "n", "p", "a", "b", "g", "v", "w",
                     "q", "u", "x", "tail", "c"]:
            with self.subTest(name=name):
                e = D0Elet(name, n(2), op("+", op("*", x(name), n(3)), x(name)))
                self.check(e, NAT, 8)

    def test_thunk_parameters_do_not_capture(self):
        # if c then u else v, with source variables named like thunk params
        e = D0Elet("u", n(5), D0Elet("v", n(6), D0Eif0(T, x("u"), x("v"))))
        self.check(e, NAT, 5)
        e = D0Elet("u", n(5), D0Elet("v", n(6), D0Eif0(F, x("u"), x("v"))))
        self.check(e, NAT, 6)
        e = D0Elet("u", T, D0Elet("v", F, op("and", T, x("u"))))
        self.check(e, BOOL, True)
        e = D0Elet("u", T, D0Elet("v", F, op("or", F, x("v"))))
        self.check(e, BOOL, False)

    def test_thunk_names_are_fresh_and_deterministic(self):
        e = D0Eif0(x("c"), x("u"), D0Eapp(x("v"), x("v_1")))
        t1, t2 = compile_expr(e), compile_expr(e)
        self.assertEqual(t1, t2)                     # deterministic
        # u occurs in the then-branch, so its thunk uses u_1; v and v_1 occur
        # in the else-branch, so its thunk uses v_2.
        self.assertEqual(show(t1),
                         "(((c (lam u_1. u)) (lam v_2. (v v_1))) (lam w. w))")

    def test_fix_binders_and_capture_hazards(self):
        # ACC-07: function name and parameter each shadow outer bindings.
        loop_body = lambda ret: D0Eif0(op("==", x("x"), n(0)), ret,
                                       D0Eapp(x("f"), op("-", x("x"), n(1))))
        # outer f is shadowed by the function name
        self.check(D0Elet("f", n(100), D0Eapp(D0Efix("f", "x", loop_body(n(0))), n(2))), NAT, 0)
        # outer x is shadowed by the parameter
        self.check(D0Elet("x", n(100), D0Eapp(D0Efix("f", "x", x("x")), n(5))), NAT, 5)
        # free variables of the body named like Z's binders g, x, v
        for outer in ["g", "v", "n"]:
            with self.subTest(outer=outer):
                e = D0Elet(outer, n(7), D0Eapp(D0Efix("f", "x", loop_body(x(outer))), n(2)))
                self.check(e, NAT, 7)

    def test_coincident_fix_binders(self):
        self.check(D0Eapp(D0Efix("f", "f", x("f")), n(3)), NAT, 3)
        self.check(D0Eapp(D0Efix("f", "f", op("+", x("f"), n(1))), n(3)), NAT, 4)
        t = compile_expr(D0Efix("f", "f", x("f")))
        self.assertEqual(t, App(Z, Lam("f", Lam("f", Var("f")))))


class TranslationShapeTests(unittest.TestCase):
    """Compositionality: the documented rules, checked on open terms."""

    def test_rules(self):
        a, b, c = x("a"), x("b"), x("c")
        A, B, C = Var("a"), Var("b"), Var("c")
        self.assertEqual(compile_expr(a), A)
        self.assertEqual(compile_expr(D0Elam("a", b)), Lam("a", B))
        self.assertEqual(compile_expr(D0Eapp(a, b)), App(A, B))
        self.assertEqual(compile_expr(D0Elet("a", b, c)), App(Lam("a", C), B))
        self.assertEqual(compile_expr(D0Eif0(a, b, c)),
                         App(apps(A, Lam("u", B), Lam("v", C)), I))
        self.assertEqual(compile_expr(D0Efix("f", "a", b)),
                         App(Z, Lam("f", Lam("a", B))))
        self.assertEqual(compile_expr(D0Epair(a, b)), apps(PAIR, A, B))
        self.assertEqual(compile_expr(D0Epfst(a)), App(FST, A))
        self.assertEqual(compile_expr(D0Epsnd(a)), App(SND, A))
        self.assertEqual(compile_expr(op("and", a, b)),
                         App(apps(A, Lam("u", B), Lam("v", FALSE)), I))
        self.assertEqual(compile_expr(op("or", a, b)),
                         App(apps(A, Lam("u", TRUE), Lam("v", B)), I))
        self.assertEqual(compile_expr(n(3)), NUM(3))


def random_source(rng, depth, names):
    """A random (possibly ill-typed, possibly open) source AST."""
    if depth == 0:
        return rng.choice([lambda: n(rng.randint(0, 3)),
                           lambda: D0Ebtf(rng.random() < 0.5),
                           lambda: x(rng.choice(names))])()
    d = depth - 1
    pick = rng.randrange(11)
    sub = lambda: random_source(rng, d, names)
    name = lambda: rng.choice(names)
    return [
        lambda: D0Elam(name(), sub()),
        lambda: D0Eapp(sub(), sub()),
        lambda: D0Elet(name(), sub(), sub()),
        lambda: D0Eif0(sub(), sub(), sub()),
        lambda: D0Efix(name(), name(), sub()),
        lambda: D0Epair(sub(), sub()),
        lambda: D0Epfst(sub()),
        lambda: D0Epsnd(sub()),
        lambda: D0Eop1("not", sub()),
        lambda: op(rng.choice(["+", "-", "*", "<", "==", "and", "or"]), sub(), sub()),
        lambda: x(name()),
    ][pick]()


class StructuralPropertyTests(unittest.TestCase):
    NAMES = ["x", "y", "s", "z", "t", "f", "u", "v", "w", "u_1", "g", "p"]

    def test_fv_preserved_pure_and_input_unchanged(self):
        rng = random.Random(413)
        for i in range(400):
            e = random_source(rng, rng.randint(0, 5), self.NAMES)
            snapshot = copy.deepcopy(e)
            with self.subTest(i=i):
                t = compile_expr(e)
                self.assertEqual(t.fv, d0exp_fvset(e))
                self.assertTrue(is_pure(t))
                self.assertEqual(e, snapshot)
                self.assertEqual(compile_expr(e), t)          # deterministic

    def test_open_expressions_with_encoding_names(self):
        e = op("+", x("s"), D0Eif0(x("t"), x("z"), op("*", x("f"), x("x"))))
        t = compile_expr(e)
        self.assertEqual(t.fv, {"s", "z", "t", "f", "x"})

    def test_compile_does_not_call_evaluator(self):
        # ACC-10: replace evaluator entry points with doubles that fail.
        boom = AssertionError("evaluator called during compilation")
        with mock.patch.object(evaluator, "evaluate", side_effect=boom), \
             mock.patch.object(evaluator._Machine, "run", side_effect=boom), \
             mock.patch.object(evaluator._Machine, "_apply", side_effect=boom):
            for e in [op("+", n(2), op("*", n(3), n(4))), LOOP(),
                      D0Eapp(FACT(), n(4))]:
                snapshot = copy.deepcopy(e)
                t = compile_expr(e)
                self.assertTrue(is_pure(t))
                self.assertEqual(t.fv, frozenset())
                self.assertEqual(e, snapshot)

    def test_diverging_program_compiles(self):
        self.assertTrue(is_pure(compile_expr(LOOP())))


class TypedProgramGenerator:
    """Random closed, well-typed programs with natural or boolean results."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.count = 0

    def name(self):
        self.count += 1
        return self.rng.choice(["x", "s", "z", "t", "f", "u", "v"]) + (
            "" if self.rng.random() < 0.5 else str(self.count))

    def nat(self, depth, env):
        r = self.rng
        if depth == 0:
            if env and r.random() < 0.5:
                return x(r.choice(env))
            return n(r.randint(0, 3))
        d = depth - 1
        pick = r.randrange(7)
        if pick == 0:
            return op(r.choice(["+", "-", "+", "-", "*"]), self.nat(d, env), self.nat(d, env))
        if pick == 1:
            return D0Eif0(self.bool(d, env), self.nat(d, env), self.nat(d, env))
        if pick == 2:
            y = self.name()
            return D0Elet(y, self.nat(d, env), self.nat(d, env + [y]))
        if pick == 3:
            y = self.name()
            return D0Eapp(D0Elam(y, self.nat(d, env + [y])), self.nat(d, env))
        if pick == 4:
            return D0Epfst(D0Epair(self.nat(d, env), self.bool(d, env)))
        if pick == 5:
            return D0Epsnd(D0Epair(self.bool(d, env), self.nat(d, env)))
        return self.nat(0, env)

    def bool(self, depth, env):
        r = self.rng
        if depth == 0:
            return D0Ebtf(r.random() < 0.5)
        d = depth - 1
        pick = r.randrange(4)
        if pick == 0:
            return op(r.choice(["<", "<=", ">", ">=", "==", "!="]),
                      self.nat(d, env), self.nat(d, env))
        if pick == 1:
            return op(r.choice(["and", "or"]), self.bool(d, env), self.bool(d, env))
        if pick == 2:
            return D0Eop1("not", self.bool(d, env))
        return D0Eif0(self.bool(d, env), self.bool(d, env), self.bool(d, env))


class DifferentialTests(unittest.TestCase):
    """Compiled answers agree with the shared evaluator on the source."""

    def test_random_typed_programs(self):
        gen = TypedProgramGenerator(2026)
        for i in range(120):
            want_nat = i % 2 == 0
            e = gen.nat(3, []) if want_nat else gen.bool(3, [])
            with self.subTest(i=i):
                expected = source_result(e)
                got = compiled_answer(e, NAT if want_nat else BOOL)
                self.assertEqual(got, expected)
                self.assertIs(type(got), type(expected))


class RejectionTests(unittest.TestCase):
    def assertRejects(self, e, *fragments):
        with self.assertRaises(CompileError) as cm:
            compile_expr(e)
        for frag in fragments:
            self.assertIn(frag, str(cm.exception))

    def test_negative_literal(self):
        self.assertRejects(n(-1), "-1", "negative")

    def test_unsupported_operators(self):
        self.assertRejects(op("/", n(4), n(2)), "'/'")
        self.assertRejects(op("%", n(4), n(2)), "'%'")
        self.assertRejects(op("&&", T, F), "'&&'")
        self.assertRejects(D0Eop1("+1", n(4)), "'+1'")
        self.assertRejects(D0Eop1("-", n(4)), "'-'")

    def test_rejected_in_unselected_branch_and_unapplied_body(self):
        self.assertRejects(D0Eif0(T, n(1), n(-3)), "-3")
        self.assertRejects(op("or", T, op("/", n(1), n(0))), "'/'")
        self.assertRejects(D0Elam("y", op("/", x("y"), n(2))), "'/'")
        self.assertRejects(D0Efix("f", "y", D0Eop1("+1", x("y"))), "'+1'")
        self.assertRejects(D0Elet("y", n(-2), n(0)), "-2")

    def test_invalid_identifier(self):
        self.assertRejects(D0Evar("1x"), "1x")


if __name__ == "__main__":
    unittest.main()
