"""Tasks 4.2, 4.3, 4.5: real Lint and Interpret, placeholders, Execute."""

import pytest

import lambda1 as L
from backend import Lambda1Backend, contains_error_value, format_value
from conftest import example, factorial_src, fibonacci_src
from contract import Artifact, Operation, Status


@pytest.fixture(scope="module")
def backend():
    return Lambda1Backend(timeout_seconds=10)


# ---- Lint ------------------------------------------------------------------

def test_lint_closed_program_passes(backend):
    r = backend.lint(example("factorial"), revision=3)
    assert (r.operation, r.revision, r.status) == (Operation.LINT, 3, Status.OK)
    assert "No free variables" in r.summary


def test_lint_open_program_lists_names_sorted(backend):
    r = backend.lint(example("undeclared"), revision=1)
    assert r.status is Status.LANGUAGE_ERROR
    assert r.summary == "Undeclared variable(s): x, y, z"
    assert r.output.splitlines()[1:] == ["  x", "  y", "  z"]


def test_lint_single_free_variable(backend):
    r = backend.lint('D0Evar("x")', revision=1)
    assert r.status is Status.LANGUAGE_ERROR and "x" in r.summary


def test_lint_does_not_evaluate(backend, monkeypatch):
    # Closed but fails at runtime: Lint must still pass ...
    r = backend.lint(example("runtime_error"), revision=1)
    assert r.status is Status.OK
    # ... and must never call the evaluator.
    def boom(*_a, **_k):
        raise AssertionError("lint evaluated the program")
    monkeypatch.setattr(L, "d0exp_evaluate", boom)
    assert backend.lint(example("runtime_error"), revision=1).status is Status.OK


def test_lint_malformed_input(backend):
    r = backend.lint(example("malformed"), revision=1)
    assert r.status is Status.INPUT_ERROR


# ---- Interpret -------------------------------------------------------------

def test_interpret_arithmetic(backend):
    r = backend.interpret(example("arithmetic"), revision=2)
    assert (r.operation, r.revision, r.status) == (Operation.INTERPRET, 2, Status.OK)
    assert r.output == "D0Vint(arg1=42)"


@pytest.mark.parametrize("n, expected", [(0, 1), (1, 1), (5, 120), (10, 3628800)])
def test_interpret_factorial(backend, n, expected):
    r = backend.interpret(factorial_src(n), revision=1)
    assert r.status is Status.OK and r.output == f"D0Vint(arg1={expected})"


@pytest.mark.parametrize("n, expected", [(0, 0), (1, 1), (2, 1), (10, 55)])
def test_interpret_fibonacci(backend, n, expected):
    r = backend.interpret(fibonacci_src(n), revision=1)
    assert r.status is Status.OK and r.output == f"D0Vint(arg1={expected})"


def test_interpret_canned_examples(backend):
    assert backend.interpret(example("factorial"), 1).output == "D0Vint(arg1=3628800)"
    assert backend.interpret(example("fibonacci"), 1).output == "D0Vint(arg1=610)"


def test_interpret_malformed_input_is_input_error(backend):
    r = backend.interpret(example("malformed"), revision=1)
    assert r.status is Status.INPUT_ERROR


@pytest.mark.parametrize("name, fragment", [
    ("runtime_error", "division by zero"),
    ("type_error", "TypeError"),
    ("deep_recursion", "recursion too deep"),
])
def test_interpret_runtime_failures(backend, name, fragment):
    r = backend.interpret(example(name), revision=1)
    assert r.status is Status.LANGUAGE_ERROR
    assert fragment in r.output


def test_interpret_error_sentinel_direct_and_in_pair(backend):
    direct = backend.interpret('D0Evar("x")', revision=1)
    assert direct.status is Status.LANGUAGE_ERROR and "D0V000" in direct.output
    paired = backend.interpret('D0Epair(D0Eint(1), D0Evar("x"))', revision=1)
    assert paired.status is Status.LANGUAGE_ERROR and "D0V000" in paired.output


def test_interpret_timeout_is_backend_failure():
    r = Lambda1Backend(timeout_seconds=0.5).interpret(example("slow_fibonacci"), 1)
    assert r.status is Status.BACKEND_FAILURE and "timed out" in r.summary


def test_format_value_and_sentinel_helpers():
    assert format_value(L.D0Vpair(L.D0Vint(1), L.D0Vbtf(True))) == \
        "D0Vpair(arg1=D0Vint(arg1=1), arg2=D0Vbtf(arg1=True))"
    lam = L.D0Vlam(L.ENVnil(), L.D0Elam("x", L.D0Evar("x")))
    assert format_value(lam).startswith("D0Vlam(<closure: lam x")
    assert contains_error_value(L.D0Vpair(L.D0Vint(1), L.D0Vpair(L.D0V000(), L.D0Vint(2))))
    assert not contains_error_value(L.D0Vint(0))


# ---- placeholders and Execute ----------------------------------------------

def test_typecheck_and_compile_are_not_implemented(backend):
    tc = backend.typecheck(example("factorial"), 4)
    cp = backend.compile(example("factorial"), 4)
    assert tc.status is Status.NOT_IMPLEMENTED and not tc.ok
    assert cp.status is Status.NOT_IMPLEMENTED and not cp.ok
    assert "not yet implemented" in tc.summary and "not yet implemented" in cp.summary
    assert cp.artifact is None


def test_execute_without_artifact_is_unavailable(backend):
    r = backend.execute(None, revision=1)
    assert r.status is Status.UNAVAILABLE
    stale = Artifact(revision=1, target="python", code="")
    assert backend.execute(stale, revision=2).status is Status.UNAVAILABLE
