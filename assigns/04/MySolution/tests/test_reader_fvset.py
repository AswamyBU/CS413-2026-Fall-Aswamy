"""Task 4.1: free-variable analysis, plus the restricted constructor reader."""

import pytest

import lambda1 as L
from backend import free_variables
from reader import MAX_DEPTH, ReadError, read_d0exp

x, y, z, f = (L.D0Evar(v) for v in "xyzf")


# ---- d0exp_fvset over every constructor ------------------------------------

@pytest.mark.parametrize("exp, expected", [
    (L.D0Eint(1), set()),
    (L.D0Ebtf(True), set()),
    (L.D0Evar("x"), {"x"}),
    (L.D0Eop1("+1", x), {"x"}),
    (L.D0Eop2("+", x, y), {"x", "y"}),
    (L.D0Elam("x", L.D0Eop2("+", x, y)), {"y"}),
    (L.D0Efix("f", "x", L.D0Eapp(f, L.D0Eop2("+", x, y))), {"y"}),
    (L.D0Eapp(x, y), {"x", "y"}),
    (L.D0Eif0(x, y, z), {"x", "y", "z"}),           # all three parts, both branches
    (L.D0Eif0(L.D0Ebtf(True), L.D0Eint(0), z), {"z"}),  # else-branch only
    (L.D0Eif0(L.D0Ebtf(True), y, L.D0Eint(0)), {"y"}),  # then-branch only
    (L.D0Elet("x", L.D0Eint(1), L.D0Eop2("+", x, y)), {"y"}),
    (L.D0Epair(x, y), {"x", "y"}),
    (L.D0Epfst(x), {"x"}),
    (L.D0Epsnd(y), {"y"}),
])
def test_fvset_each_constructor(exp, expected):
    result = L.d0exp_fvset(exp)
    assert isinstance(result, frozenset)
    assert result == frozenset(expected)


def test_fvset_duplicates_reported_once():
    exp = L.D0Eop2("+", x, L.D0Eop2("*", x, x))
    assert L.d0exp_fvset(exp) == frozenset({"x"})


def test_fvset_nested_bindings_and_shadowing():
    # lam x. lam y. x + y + z   -> only z free
    inner = L.D0Elam("y", L.D0Eop2("+", L.D0Eop2("+", x, y), z))
    assert L.d0exp_fvset(L.D0Elam("x", inner)) == frozenset({"z"})
    # (lam x. x) applied to x  -> outer x is free
    assert L.d0exp_fvset(L.D0Eapp(L.D0Elam("x", x), x)) == frozenset({"x"})
    # Inner binding of the same name shadows, outer one still binds
    shadow = L.D0Elam("x", L.D0Eapp(L.D0Elam("x", x), x))
    assert L.d0exp_fvset(shadow) == frozenset()


def test_fvset_recursive_function_binds_name_and_param():
    body = L.D0Eapp(f, x)
    assert L.d0exp_fvset(L.D0Efix("f", "x", body)) == frozenset()
    # outside the fix, f is not bound
    outside = L.D0Eapp(L.D0Efix("f", "x", body), f)
    assert L.d0exp_fvset(outside) == frozenset({"f"})


def test_fvset_let_initializer_not_in_scope():
    # let x = x + 1 in x   -> the initializer's x is free
    exp = L.D0Elet("x", L.D0Eop2("+", x, L.D0Eint(1)), x)
    assert L.d0exp_fvset(exp) == frozenset({"x"})


def test_fvset_unused_binding_is_fine():
    assert L.d0exp_fvset(L.D0Elam("unused", L.D0Eint(3))) == frozenset()


def test_free_variables_from_source_text():
    assert free_variables('D0Elet("z", D0Evar("z"), D0Evar("y"))') == frozenset({"z", "y"})


# ---- restricted reader ----------------------------------------------------

def test_reader_builds_nested_multiline_with_comments():
    src = '''
    # a comment
    D0Eop2("+",          # trailing comment
           D0Eint(20),
           D0Eint(-22))
    '''
    assert read_d0exp(src) == L.D0Eop2("+", L.D0Eint(20), L.D0Eint(-22))


def test_reader_accepts_keyword_arguments():
    assert read_d0exp('D0Elam(arg1="x", arg2=D0Evar(arg1="x"))') == L.D0Elam("x", x)


@pytest.mark.parametrize("src, fragment", [
    ('', "empty"),
    ('42', "constructor call"),
    ('D0Eint(1) + D0Eint(2)', "constructor call"),
    ('__import__("os").system("echo hi")', "constructor call"),
    ('open("secret.txt")', "unknown constructor"),
    ('D0Eint(1); D0Eint(2)', "syntax error"),
    ('D0Eint(True)', "integer literal"),
    ('D0Eint("1")', "integer literal"),
    ('D0Ebtf(1)', "True or False"),
    ('D0Evar(42)', "variable-name"),
    ('D0Evar("")', "variable-name"),
    ('D0Eop2("%", D0Eint(1), D0Eint(2))', "binary operator"),
    ('D0Eop1("neg", D0Eint(1))', "unary operator"),
    ('D0Eint(1, 2)', "takes 1 argument"),
    ('D0Eop2("+", D0Eint(1))', "missing field"),
    ('D0Eint(bogus=1)', "no field"),
    ('D0Eint(*[1])', "not allowed"),
    ('D0Epfst(D0Eint)', "constructor call"),
    ('D0Evar(x)', "variable-name"),
])
def test_reader_rejects_bad_input(src, fragment):
    with pytest.raises(ReadError, match=fragment):
        read_d0exp(src)


def test_reader_rejects_excessive_nesting():
    src = "D0Eop1(\"+1\", " * (MAX_DEPTH + 5) + "D0Eint(0)" + ")" * (MAX_DEPTH + 5)
    with pytest.raises(ReadError, match="nest"):
        read_d0exp(src)
