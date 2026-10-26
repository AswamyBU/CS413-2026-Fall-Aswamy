"""Compiler from extended LAMBDA source ASTs to pure lambda terms.

Entry point: ``compile_expr(source) -> Term``.

The compiler is a ``D0ExpVisitor``: each ``visit_*`` method compiles the
children of one source constructor and combines their translations. It
never evaluates anything (this module does not import the evaluator), so a
diverging program compiles like any other. The translation rules are listed
in DESIGN.md and next to each method below.

Freshness policy. The only binders the compiler ever puts *around* a
translated subterm are the thunk parameters of delayed branches. A thunk
around term ``T`` uses ``fresh_name(base, all_names(T))``: the base name
(``u`` for a then-branch / right operand, ``v`` for an else-branch) if it
does not occur anywhere in ``T``, otherwise the first of ``base_1``,
``base_2``, ... that does not. This is deterministic, and since the name does
not occur in ``T`` at all it cannot capture a free variable of ``T``. Source
binders (lambda, let, fix) are kept as written. Library combinators are
closed and only ever applied to translated terms, so their internal binder
names cannot capture anything either.
"""
from __future__ import annotations

from church import (
    ADD, EQ, FALSE, FST, GEQ, GT, I, LEQ, LT, MUL, NEQ, NOT, NUM, PAIR, SND,
    SUB, TRUE, Z, apps,
)
from source_syntax import (
    D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0ExpVisitor, D0Evar, d0exp, pretty,
)
from target import App, Lam, Term, Var, all_names, fresh_name, is_identifier

__all__ = ["CompileError", "CompileVisitor", "compile_expr", "ARITHMETIC",
           "SUPPORTED_OP1", "SUPPORTED_OP2"]


class CompileError(ValueError):
    """Raised for source forms outside the project's language."""


# Strict binary operators: C[e1 op e2] = OP C[e1] C[e2].
ARITHMETIC: dict[str, Term] = {
    "+": ADD, "-": SUB, "*": MUL,
    "<": LT, "<=": LEQ, ">": GT, ">=": GEQ, "==": EQ, "!=": NEQ,
}
SUPPORTED_OP1 = frozenset({"not"})
SUPPORTED_OP2 = frozenset(ARITHMETIC) | {"and", "or"}


def _thunk(body: Term, base: str) -> Term:
    """``lam p. body`` with ``p`` fresh against every name in ``body``."""
    return Lam(fresh_name(base, all_names(body)), body)


def _force(selector: Term, then_term: Term, else_term: Term) -> Term:
    """``(selector (lam u. then) (lam v. else)) I``: the boolean picks one
    thunk, and only that thunk is applied to the dummy value I."""
    return App(apps(selector, _thunk(then_term, "u"), _thunk(else_term, "v")), I)


def _check_name(name: object, where: d0exp) -> str:
    if not is_identifier(name):
        raise CompileError(f"invalid identifier {name!r} in {pretty(where)}")
    return name


class CompileVisitor(D0ExpVisitor[Term]):
    """Translate one source expression. The visitor holds no state."""

    # C[n] = NUM(n)            (n >= 0)
    def visit_int(self, dexp: D0Eint) -> Term:
        n = dexp.arg1
        if isinstance(n, bool) or not isinstance(n, int):
            raise CompileError(f"integer literal expected, got {n!r}")
        if n < 0:
            raise CompileError(
                f"unsupported negative integer literal {n}: "
                "the source language has natural numbers only")
        return NUM(n)

    # C[true] = TRUE,  C[false] = FALSE
    def visit_btf(self, dexp: D0Ebtf) -> Term:
        return TRUE if dexp.arg1 else FALSE

    # C[x] = x
    def visit_var(self, dexp: D0Evar) -> Term:
        return Var(_check_name(dexp.arg1, dexp))

    # C[lam x. e] = lam x. C[e]
    def visit_lam(self, dexp: D0Elam) -> Term:
        x = _check_name(dexp.arg1, dexp)
        return Lam(x, dexp.arg2.accept(self))

    # C[fix f(x). e] = Z (lam f. lam x. C[e])
    # If f == x the inner lam x shadows lam f, exactly as the source rule says.
    def visit_fix(self, dexp: D0Efix) -> Term:
        f = _check_name(dexp.arg1, dexp)
        x = _check_name(dexp.arg2, dexp)
        return App(Z, Lam(f, Lam(x, dexp.arg3.accept(self))))

    # C[e1 e2] = C[e1] C[e2]
    def visit_app(self, dexp: D0Eapp) -> Term:
        return App(dexp.arg1.accept(self), dexp.arg2.accept(self))

    # C[if c then t else f] = (C[c] (lam u. C[t]) (lam v. C[f])) I
    def visit_if0(self, dexp: D0Eif0) -> Term:
        cond = dexp.arg1.accept(self)
        then_t = dexp.arg2.accept(self)
        else_t = dexp.arg3.accept(self)
        return _force(cond, then_t, else_t)

    # C[let x = e1 in e2] = (lam x. C[e2]) C[e1]
    def visit_let(self, dexp: D0Elet) -> Term:
        x = _check_name(dexp.arg1, dexp)
        init = dexp.arg2.accept(self)
        body = dexp.arg3.accept(self)
        return App(Lam(x, body), init)

    # C[pair e1 e2] = PAIR C[e1] C[e2]
    def visit_pair(self, dexp: D0Epair) -> Term:
        return apps(PAIR, dexp.arg1.accept(self), dexp.arg2.accept(self))

    # C[fst e] = FST C[e]
    def visit_pfst(self, dexp: D0Epfst) -> Term:
        return App(FST, dexp.arg1.accept(self))

    # C[snd e] = SND C[e]
    def visit_psnd(self, dexp: D0Epsnd) -> Term:
        return App(SND, dexp.arg1.accept(self))

    # C[not e] = NOT C[e]
    def visit_op1(self, dexp: D0Eop1) -> Term:
        if dexp.name not in SUPPORTED_OP1:
            raise CompileError(
                f"unsupported unary operator {dexp.name!r} in {pretty(dexp)}; "
                f"supported: {sorted(SUPPORTED_OP1)}")
        return App(NOT, dexp.arg1.accept(self))

    # C[e1 op e2]    = OP C[e1] C[e2]                       (op arithmetic/comparison)
    # C[e1 and e2]   = (C[e1] (lam u. C[e2]) (lam v. FALSE)) I
    # C[e1 or e2]    = (C[e1] (lam u. TRUE) (lam v. C[e2])) I
    def visit_op2(self, dexp: D0Eop2) -> Term:
        op = dexp.name
        if op not in SUPPORTED_OP2:
            raise CompileError(
                f"unsupported binary operator {op!r} in {pretty(dexp)}; "
                f"supported: {sorted(SUPPORTED_OP2)}")
        left = dexp.arg1.accept(self)
        right = dexp.arg2.accept(self)
        if op == "and":
            return _force(left, right, FALSE)
        if op == "or":
            return _force(left, TRUE, right)
        return apps(ARITHMETIC[op], left, right)


def compile_expr(source: d0exp) -> Term:
    """Compile a source AST (open or closed) to a pure target term.

    Raises ``CompileError`` for a negative literal, an unsupported operator,
    or an invalid identifier anywhere in the tree, including unselected
    branches and unapplied function bodies. The input is not modified.
    """
    return source.accept(CompileVisitor())
