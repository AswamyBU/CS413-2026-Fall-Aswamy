"""The single shared evaluator for source ASTs and target terms.

    evaluate(expr, budget=None, *, trace=None) -> EvalResult

``expr`` may be a source AST (``D0E000``) or a target ``Term``. Both are run
by the same machine, ``_Machine``, which is a ``D0ExpVisitor``. Target terms
use the same ``accept`` protocol as the source AST, so a target ``Var``,
``Lam`` or ``App`` is handled by exactly the same ``visit_var``,
``visit_lam`` and ``visit_app`` methods as a source ``D0Evar``, ``D0Elam``
or ``D0Eapp``. The other ten ``visit_*`` methods implement source-only
constructors with the source rules; a target term can never reach them.

Strategy: weak, left-to-right call-by-value, by substitution.
  * A lambda (and, in the source, a fix, number, boolean, or pair of values)
    is a value. Nothing is evaluated under a lambda; there is no eta rule.
  * In an application, evaluate the function, then the argument, then do one
    beta-value step:  (lam x. body) v  -->  body[x := v].
  * The machine is iterative (an explicit continuation stack), so long
    computations do not use Python recursion.

Budget: ``budget`` is the maximum number of beta-value steps (``None`` means
unlimited). Only beta-value steps count; alpha-renaming does not. If a beta
step is needed when ``steps == budget``, the result is ``"exhausted"``. A
value reached on the last allowed step is ``"value"``. A value completes in
zero steps, even with budget 0.

Target execution is restricted to closed terms: ``evaluate`` raises
``EvalError`` for a target term with free variables. Source evaluation
raises ``EvalError`` for an unbound variable, a type error, or a negative
literal / unsupported operator when it is reached.

This module never imports the compiler, and the target path never performs a
source operation or recognises a Church encoding.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from source_syntax import (
    D0E000, D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1,
    D0Eop2, D0Epair, D0Epfst, D0Epsnd, D0ExpVisitor, D0Evar, pretty,
    source_substitute,
)
from target import Lam, Term, show, substitute

__all__ = ["EvalResult", "EvalError", "evaluate", "VALUE", "EXHAUSTED"]

VALUE = "value"
EXHAUSTED = "exhausted"


class EvalError(Exception):
    """A run-time error: open target term, unbound variable, type error."""


@dataclass(frozen=True)
class EvalResult:
    status: str            # VALUE or EXHAUSTED
    value: Any             # the value (a Lam or a source value), or None
    steps: int             # beta-value steps performed
    budget: int | None     # the budget that was given

    @property
    def completed(self) -> bool:
        return self.status == VALUE


class _Exhausted(Exception):
    pass


_EVAL, _RETURN = 0, 1
_Instr = tuple[int, Any]


class _Machine(D0ExpVisitor[_Instr]):
    """One run of the evaluator. ``visit_*`` methods return the next
    instruction: ``(_EVAL, expr)`` or ``(_RETURN, value)``. Pending work is
    kept as continuation closures on ``self.stack``."""

    def __init__(self, budget: int | None,
                 trace: list[tuple[Any, Any]] | None) -> None:
        self.budget = budget
        self.trace = trace
        self.steps = 0
        self.stack: list[Callable[[Any], _Instr]] = []

    def run(self, expr: Any) -> Any:
        instr: _Instr = (_EVAL, expr)
        while True:
            mode, x = instr
            if mode == _EVAL:
                instr = x.accept(self)
            elif self.stack:
                instr = self.stack.pop()(x)
            else:
                return x

    def _then(self, k: Callable[[Any], _Instr], expr: Any) -> _Instr:
        """Evaluate ``expr``, then continue with ``k(value)``."""
        self.stack.append(k)
        return (_EVAL, expr)

    # -- shared by both languages: variables, lambdas, applications --------

    def visit_var(self, node) -> _Instr:
        # With substitution, a variable is only reached if it is unbound.
        raise EvalError(f"unbound variable {node.arg1!r}")

    def visit_lam(self, node) -> _Instr:
        return (_RETURN, node)

    def visit_app(self, node) -> _Instr:
        fn, arg = node.arg1, node.arg2
        return self._then(lambda f: self._then(lambda a: self._apply(f, a), arg), fn)

    def _apply(self, fn: Any, arg: Any) -> _Instr:
        """One beta-value step; ``fn`` and ``arg`` are already values."""
        if self.budget is not None and self.steps >= self.budget:
            raise _Exhausted
        if isinstance(fn, Lam):                       # target
            body = substitute(fn.arg2, fn.arg1, arg)
        elif isinstance(fn, D0Elam):                  # source lambda
            body = source_substitute(fn.arg2, fn.arg1, arg)
        elif isinstance(fn, D0Efix):                  # source fix f(x). e
            f, x, body = fn.arg1, fn.arg2, fn.arg3
            if f != x:                                # if f == x, x shadows f
                body = source_substitute(body, f, fn)
            body = source_substitute(body, x, arg)
        else:
            raise EvalError(f"cannot apply a non-function value: {_show(fn)}")
        self.steps += 1
        if self.trace is not None:
            self.trace.append((fn, arg))
        return (_EVAL, body)

    # -- source-only constructors ------------------------------------------

    def visit_int(self, node: D0Eint) -> _Instr:
        if node.arg1 < 0:
            raise EvalError(f"unsupported negative literal {node.arg1}")
        return (_RETURN, node)

    def visit_btf(self, node: D0Ebtf) -> _Instr:
        return (_RETURN, node)

    def visit_fix(self, node: D0Efix) -> _Instr:
        return (_RETURN, node)

    def visit_if0(self, node: D0Eif0) -> _Instr:
        def choose(c):
            return (_EVAL, node.arg2 if _bool(c) else node.arg3)
        return self._then(choose, node.arg1)

    def visit_let(self, node: D0Elet) -> _Instr:
        x, body = node.arg1, node.arg3
        return self._then(lambda v: (_EVAL, source_substitute(body, x, v)), node.arg2)

    def visit_pair(self, node: D0Epair) -> _Instr:
        right = node.arg2
        return self._then(
            lambda a: self._then(lambda b: (_RETURN, D0Epair(a, b)), right),
            node.arg1)

    def visit_pfst(self, node: D0Epfst) -> _Instr:
        return self._then(lambda p: (_RETURN, _pair(p).arg1), node.arg1)

    def visit_psnd(self, node: D0Epsnd) -> _Instr:
        return self._then(lambda p: (_RETURN, _pair(p).arg2), node.arg1)

    def visit_op1(self, node: D0Eop1) -> _Instr:
        if node.name != "not":
            raise EvalError(f"unsupported unary operator {node.name!r}")
        return self._then(lambda b: (_RETURN, D0Ebtf(not _bool(b))), node.arg1)

    def visit_op2(self, node: D0Eop2) -> _Instr:
        op, right = node.name, node.arg2
        if op == "and":       # right operand only if the left is true
            return self._then(
                lambda a: (_EVAL, right) if _bool(a) else (_RETURN, D0Ebtf(False)),
                node.arg1)
        if op == "or":        # right operand only if the left is false
            return self._then(
                lambda a: (_RETURN, D0Ebtf(True)) if _bool(a) else (_EVAL, right),
                node.arg1)
        if op not in _NAT_OPS:
            raise EvalError(f"unsupported binary operator {op!r}")
        compute = _NAT_OPS[op]
        return self._then(
            lambda a: self._then(lambda b: (_RETURN, compute(_nat(a), _nat(b))), right),
            node.arg1)


# Source arithmetic on naturals (source rules, used only on source ASTs).
_NAT_OPS: dict[str, Callable[[int, int], D0E000]] = {
    "+": lambda m, n: D0Eint(m + n),
    "-": lambda m, n: D0Eint(max(m - n, 0)),   # truncated subtraction
    "*": lambda m, n: D0Eint(m * n),
    "<": lambda m, n: D0Ebtf(m < n),
    "<=": lambda m, n: D0Ebtf(m <= n),
    ">": lambda m, n: D0Ebtf(m > n),
    ">=": lambda m, n: D0Ebtf(m >= n),
    "==": lambda m, n: D0Ebtf(m == n),
    "!=": lambda m, n: D0Ebtf(m != n),
}


def _show(v: Any) -> str:
    return show(v) if isinstance(v, Term) else pretty(v)


def _nat(v: Any) -> int:
    if not isinstance(v, D0Eint):
        raise EvalError(f"natural number expected: {_show(v)}")
    return v.arg1


def _bool(v: Any) -> bool:
    if not isinstance(v, D0Ebtf):
        raise EvalError(f"boolean expected: {_show(v)}")
    return v.arg1


def _pair(v: Any) -> D0Epair:
    if not isinstance(v, D0Epair):
        raise EvalError(f"pair expected: {_show(v)}")
    return v


def evaluate(expr: Term | D0E000, budget: int | None = None, *,
             trace: list[tuple[Any, Any]] | None = None) -> EvalResult:
    """Evaluate a source AST or a closed target term (see module docstring).

    ``trace``, if given, receives ``(function_value, argument_value)`` for
    every beta-value step, in order. The input is never modified.
    """
    if budget is not None and (isinstance(budget, bool)
                               or not isinstance(budget, int) or budget < 0):
        raise ValueError(f"budget must be a nonnegative int or None, got {budget!r}")
    if isinstance(expr, Term):
        if expr.fv:
            raise EvalError("target execution needs a closed term; free variables: "
                            + ", ".join(sorted(expr.fv)))
    elif not isinstance(expr, D0E000):
        raise TypeError(f"not a source AST or target term: {expr!r}")
    machine = _Machine(budget, trace)
    try:
        value = machine.run(expr)
    except _Exhausted:
        return EvalResult(EXHAUSTED, None, machine.steps, budget)
    return EvalResult(VALUE, value, machine.steps, budget)
