"""pytest suite for PrettyPrintVisitor and SubstitutionVisitor.

Run from assigns/05:
    python -m pytest MySolution/TEST/test_pytest_visitors.py -v
"""
import copy
from pathlib import Path
import sys

import pytest

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
P = d0exp_pretty


def add(a, b):
    return D0Eop2("+", a, b)


def S(e, x, r):
    return P(d0exp_substitute(e, x, r))


# A body that mentions x, f, and n, used for the fix cases.
FIX_FN = D0Efix("f", "n", add(V("x"), D0Eapp(V("f"), V("n"))))


########################################################################
# Pretty printing
########################################################################

@pytest.mark.parametrize("e, expected", [
    (I(42), "42"),
    (I(0), "0"),
    (I(-17), "-17"),
    (I(10 ** 30), "1" + "0" * 30),
    (I(-(2 ** 100)), str(-(2 ** 100))),
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
    (D0Eapp(D0Elam("x", add(V("x"), I(1))), I(4)), "((lam x. (x + 1)) 4)"),
])
def test_pretty_constructors(e, expected):
    assert P(e) == expected
    assert e.accept(PrettyPrintVisitor()) == expected
    assert P(e) == P(e).strip() and "\n" not in P(e)


def test_pretty_nested():
    fact = D0Efix("f", "n", D0Eif0(
        D0Eop2("<=", V("n"), I(0)), I(1),
        D0Eop2("*", V("n"), D0Eapp(V("f"), D0Eop2("-", V("n"), I(1))))))
    e = D0Elet("p", D0Epair(D0Eapp(fact, I(5)), D0Eop1("not", D0Ebtf(True))),
               D0Epair(D0Epsnd(V("p")), D0Epfst(V("p"))))
    assert P(e) == ("(let p = (pair ((fix f(n). (if (n <= 0) then 1 else"
                    " (n * (f (n - 1))))) 5) (not true)) in (pair (snd p) (fst p)))")


def test_pretty_does_not_evaluate():
    assert P(D0Eop2("/", I(1), I(0))) == "(1 / 0)"
    assert P(D0Eapp(D0Efix("f", "x", D0Eapp(V("f"), V("x"))), I(0))) == "((fix f(x). (f x)) 0)"
    assert P(D0Eop2("+", D0Ebtf(True), I(1))) == "(true + 1)"


########################################################################
# Substitution: spec examples and every constructor
########################################################################

@pytest.mark.parametrize("e, x, r, expected", [
    (add(V("x"), V("z")), "x", I(3), "(3 + z)"),
    (D0Elam("x", add(V("x"), V("y"))), "x", I(3), "(lam x. (x + y))"),
    (D0Elam("y", add(V("x"), V("y"))), "x", V("y"), "(lam y_1. (y + y_1))"),
    (D0Elet("x", V("x"), add(V("x"), V("y"))), "x", I(3), "(let x = 3 in (x + y))"),
    (D0Elet("y", V("x"), add(V("x"), V("y"))), "x", V("y"), "(let y_1 = y in (y + y_1))"),
    (FIX_FN, "x", V("f"), "(fix f_1(n). (f + (f_1 n)))"),
    (V("x"), "x", add(V("x"), I(1)), "(x + 1)"),
])
def test_substitute_assignment_examples(e, x, r, expected):
    assert S(e, x, r) == expected


R = add(V("a"), I(1))


@pytest.mark.parametrize("e, expected", [
    (I(7), "7"),
    (D0Ebtf(True), "true"),
    (D0Ebtf(False), "false"),
    (V("x"), "(a + 1)"),
    (V("z"), "z"),
    (D0Eop1("-", V("x")), "(- (a + 1))"),
    (D0Eop2("*", V("x"), V("z")), "((a + 1) * z)"),
    (D0Elam("z", V("x")), "(lam z. (a + 1))"),
    (D0Efix("g", "z", D0Eapp(V("g"), V("x"))), "(fix g(z). (g (a + 1)))"),
    (D0Eapp(V("x"), V("x")), "((a + 1) (a + 1))"),
    (D0Eif0(V("x"), V("x"), V("w")), "(if (a + 1) then (a + 1) else w)"),
    (D0Elet("z", V("x"), V("x")), "(let z = (a + 1) in (a + 1))"),
    (D0Epair(V("x"), I(2)), "(pair (a + 1) 2)"),
    (D0Epfst(V("x")), "(fst (a + 1))"),
    (D0Epsnd(V("x")), "(snd (a + 1))"),
])
def test_substitute_every_constructor(e, expected):
    assert S(e, "x", R) == expected
    direct = e.accept(SubstitutionVisitor({"x": R}, FreshNames({"x", "a"})))
    assert P(direct) == expected


@pytest.mark.parametrize("op", ["+", "-", "*", "/", "<", "<=", "=", "!="])
def test_substitute_preserves_operator(op):
    assert d0exp_substitute(D0Eop2(op, V("x"), V("x")), "x", I(2)) == D0Eop2(op, I(2), I(2))


def test_substitute_replacement_contains_target():
    assert S(add(V("x"), V("x")), "x", add(V("x"), I(1))) == "((x + 1) + (x + 1))"
    assert S(D0Elam("y", V("x")), "x", D0Eapp(V("x"), V("x"))) == "(lam y. (x x))"


def test_substitute_nonmatching_variable():
    e = D0Elam("y", add(V("y"), V("z")))
    assert d0exp_substitute(e, "x", V("y")) == e


########################################################################
# Shadowing
########################################################################

@pytest.mark.parametrize("e, x, expected", [
    (D0Epair(V("x"), D0Elam("x", V("x"))), "x", "(pair 9 (lam x. x))"),
    (D0Epair(V("f"), D0Efix("f", "n", D0Eapp(V("f"), V("n")))), "f",
     "(pair 9 (fix f(n). (f n)))"),
    (D0Efix("f", "n", add(V("n"), V("m"))), "n", "(fix f(n). (n + m))"),
    (D0Efix("n", "n", add(V("n"), V("x"))), "n", "(fix n(n). (n + x))"),
    (D0Elet("x", add(V("x"), I(1)), V("x")), "x", "(let x = (9 + 1) in x)"),
    (D0Elam("y", D0Eapp(V("x"), D0Elam("x", V("x")))), "x", "(lam y. (9 (lam x. x)))"),
])
def test_shadowing(e, x, expected):
    assert S(e, x, I(9)) == expected


def test_fix_same_name_capture_keeps_parameter_shadowing():
    out = d0exp_substitute(D0Efix("n", "n", add(V("n"), V("x"))), "x", V("n"))
    assert P(out) == "(fix n_1(n_1). (n_1 + n))"
    assert out.arg1 == out.arg2


########################################################################
# Capture avoidance
########################################################################

@pytest.mark.parametrize("e, r, expected", [
    (D0Elam("y", add(V("x"), V("y"))), V("y"), "(lam y_1. (y + y_1))"),
    (D0Elet("y", I(1), add(V("x"), V("y"))), V("y"), "(let y_1 = 1 in (y + y_1))"),
    (FIX_FN, V("f"), "(fix f_1(n). (f + (f_1 n)))"),
    (FIX_FN, V("n"), "(fix f(n_1). (n + (f n_1)))"),
    (FIX_FN, D0Eapp(V("f"), V("n")), "(fix f_1(n_1). ((f n) + (f_1 n_1)))"),
])
def test_capture_avoidance(e, r, expected):
    assert S(e, "x", r) == expected


def test_capturing_result_is_not_produced():
    assert S(D0Elam("y", add(V("x"), V("y"))), "x", V("y")) != "(lam y. (y + y))"


@pytest.mark.parametrize("e, r, expected", [
    (D0Elam("y", V("y")), V("y"), "(lam y. y)"),
    (D0Elam("x", V("y")), V("y"), "(lam x. y)"),
    (D0Efix("f", "n", V("n")), V("f"), "(fix f(n). n)"),
    (FIX_FN, V("z"), "(fix f(n). (z + (f n)))"),
])
def test_no_unnecessary_renaming(e, r, expected):
    assert S(e, "x", r) == expected


########################################################################
# Renaming scope and fresh names
########################################################################

def test_nested_shadowing_during_renaming():
    e = D0Elam("y", add(V("x"), D0Eapp(D0Elam("y", add(V("x"), V("y"))), V("y"))))
    assert S(e, "x", V("y")) == "(lam y_1. (y + ((lam y_2. (y + y_2)) y_1)))"


def test_inner_shadow_without_target_keeps_name():
    e = D0Elam("y", D0Eapp(D0Elam("y", V("y")), add(V("x"), V("y"))))
    assert S(e, "x", V("y")) == "(lam y_1. ((lam y. y) (y + y_1)))"


def test_fresh_avoids_existing_bound_name():
    e = D0Elam("y", D0Elam("y_1", add(V("x"), add(V("y"), V("y_1")))))
    assert S(e, "x", V("y")) == "(lam y_2. (lam y_1. (y + (y_2 + y_1))))"


def test_fresh_avoids_replacement_and_free_names():
    e = D0Elam("y", add(V("x"), add(V("y"), V("y_1"))))
    assert S(e, "x", add(V("y"), V("y_2"))) == "(lam y_3. ((y + y_2) + (y_3 + y_1)))"


def test_fresh_avoids_names_generated_earlier():
    e = D0Epair(D0Elam("y", add(V("x"), V("y"))), D0Elam("y", add(V("x"), V("y"))))
    assert S(e, "x", V("y")) == "(pair (lam y_1. (y + y_1)) (lam y_2. (y + y_2)))"


def test_fresh_avoids_target():
    e = D0Elam("x", D0Elam("y", add(V("x_1"), V("y"))))
    assert S(e, "x_1", V("x")) == "(lam x_2. (lam y. (x + y)))"


def test_fresh_name_supply():
    fresh = FreshNames({"a", "a_1", "a_3"})
    assert [fresh.fresh("a") for _ in range(3)] == ["a_2", "a_4", "a_5"]


def test_all_names_visitor():
    e = D0Elet("a", V("b"), D0Efix("c", "d", D0Elam("e", V("f"))))
    assert d0exp_names(e) == frozenset("abcdef")


########################################################################
# Let initializer vs body
########################################################################

@pytest.mark.parametrize("e, r, expected", [
    (D0Elet("x", V("x"), V("x")), I(3), "(let x = 3 in x)"),
    (D0Elet("y", add(V("y"), V("x")), add(V("x"), V("y"))), V("y"),
     "(let y_1 = (y + y) in (y + y_1))"),
    (D0Elet("y", V("x"), V("y")), V("y"), "(let y = y in y)"),
])
def test_let_initializer_vs_body(e, r, expected):
    assert S(e, "x", r) == expected


########################################################################
# Preservation, determinism, no evaluation
########################################################################

def test_inputs_not_mutated():
    e = D0Elam("y", D0Elet("y", V("x"), D0Efix("f", "n", add(V("x"), V("f")))))
    r = D0Eapp(V("y"), V("f"))
    e0, r0 = copy.deepcopy(e), copy.deepcopy(r)
    d0exp_substitute(e, "x", r)
    d0exp_pretty(e)
    assert e == e0
    assert r == r0


def test_deterministic():
    e = D0Efix("f", "n", D0Elam("y", add(V("x"), D0Eapp(V("f"), V("y")))))
    r = D0Epair(V("f"), V("y"))
    outs = {P(d0exp_substitute(e, "x", r)) for _ in range(5)}
    assert outs == {"(fix f_1(n). (lam y_1. ((pair f y) + (f_1 y_1))))"}


def test_substitution_does_not_evaluate(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("evaluation attempted")
    monkeypatch.setattr(L, "d0exp_evaluate", boom)
    monkeypatch.setattr(L.EvaluateVisitor, "visit_app", boom)
    monkeypatch.setattr(L.EvaluateVisitor, "visit_op2", boom)
    omega = D0Eapp(D0Efix("f", "z", D0Eapp(V("f"), V("z"))), V("x"))
    e = D0Epair(D0Eop2("/", V("x"), I(0)), omega)
    assert S(e, "x", I(1)) == "(pair (1 / 0) ((fix f(z). (f z)) 1))"


########################################################################
# Free-variable property
########################################################################

@pytest.mark.parametrize("e, x, r", [
    (add(V("x"), V("z")), "x", I(3)),
    (D0Elam("y", add(V("x"), V("y"))), "x", V("y")),
    (D0Elet("y", V("x"), add(V("x"), V("y"))), "x", V("y")),
    (FIX_FN, "x", D0Eapp(V("f"), V("n"))),
    (D0Efix("n", "n", add(V("x"), V("n"))), "x", V("n")),
    (V("x"), "x", add(V("x"), V("q"))),
    (D0Elam("y", D0Eapp(D0Elam("y", V("x")), V("y"))), "x", D0Epair(V("y"), V("w"))),
])
def test_fv_property_when_free(e, x, r):
    assert x in d0exp_fvset(e)
    out = d0exp_substitute(e, x, r)
    assert d0exp_fvset(out) == (d0exp_fvset(e) - {x}) | d0exp_fvset(r)


@pytest.mark.parametrize("e, x, r", [
    (D0Elam("x", add(V("x"), V("y"))), "x", V("y")),
    (D0Elet("x", I(1), V("x")), "x", V("z")),
    (D0Efix("x", "n", V("x")), "x", V("n")),
    (D0Efix("f", "x", V("x")), "x", V("f")),
    (add(V("a"), V("b")), "x", V("a")),
])
def test_unchanged_when_not_free(e, x, r):
    assert x not in d0exp_fvset(e)
    out = d0exp_substitute(e, x, r)
    assert out == e
    assert d0exp_fvset(out) == d0exp_fvset(e)
