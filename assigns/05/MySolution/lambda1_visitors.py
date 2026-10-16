"""Pretty printing and capture-avoiding substitution for LAMBDA, as visitors.

Both operations are new D0ExpVisitor subclasses over the unchanged expression
classes in ../lambda1_vp.py. Every traversal (printing, substitution, name
collection) dispatches through ``accept``; nothing here evaluates.

Requires Python 3.12 or later.
"""
from __future__ import annotations

from pathlib import Path
import sys

# lambda1_vp.py lives one directory up, in assigns/05.
_ASSIGN_DIR = str(Path(__file__).resolve().parent.parent)
if _ASSIGN_DIR not in sys.path:
    sys.path.insert(0, _ASSIGN_DIR)

from lambda1_vp import (  # noqa: E402
    D0ExpVisitor, d0exp, dvar, d0exp_fvset,
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar, D0Elam, D0Efix,
    D0Eapp, D0Eif0, D0Elet, D0Epair, D0Epfst, D0Epsnd,
)

__all__ = [
    "PrettyPrintVisitor", "d0exp_pretty",
    "AllNamesVisitor", "d0exp_names",
    "FreshNames", "SubstitutionVisitor", "d0exp_substitute",
]


########################################################################
# Task 1: pretty printing
########################################################################

class PrettyPrintVisitor(D0ExpVisitor[str]):
    """Render an expression as a single fully parenthesized line."""

    def visit_int(self, dexp: D0Eint) -> str:
        return str(int(dexp.arg1))

    def visit_btf(self, dexp: D0Ebtf) -> str:
        return "true" if dexp.arg1 else "false"

    def visit_var(self, dexp: D0Evar) -> str:
        return dexp.arg1

    def visit_op1(self, dexp: D0Eop1) -> str:
        return f"({dexp.name} {dexp.arg1.accept(self)})"

    def visit_op2(self, dexp: D0Eop2) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.name} {dexp.arg2.accept(self)})"

    def visit_lam(self, dexp: D0Elam) -> str:
        return f"(lam {dexp.arg1}. {dexp.arg2.accept(self)})"

    def visit_fix(self, dexp: D0Efix) -> str:
        return f"(fix {dexp.arg1}({dexp.arg2}). {dexp.arg3.accept(self)})"

    def visit_app(self, dexp: D0Eapp) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_if0(self, dexp: D0Eif0) -> str:
        return (f"(if {dexp.arg1.accept(self)} then {dexp.arg2.accept(self)}"
                f" else {dexp.arg3.accept(self)})")

    def visit_let(self, dexp: D0Elet) -> str:
        return (f"(let {dexp.arg1} = {dexp.arg2.accept(self)}"
                f" in {dexp.arg3.accept(self)})")

    def visit_pair(self, dexp: D0Epair) -> str:
        return f"(pair {dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_pfst(self, dexp: D0Epfst) -> str:
        return f"(fst {dexp.arg1.accept(self)})"

    def visit_psnd(self, dexp: D0Epsnd) -> str:
        return f"(snd {dexp.arg1.accept(self)})"


def d0exp_pretty(dexp: d0exp) -> str:
    """Pretty-print an expression without evaluating it."""
    return dexp.accept(PrettyPrintVisitor())


########################################################################
# Helper: every name in an expression (free, bound, and binders)
########################################################################

class AllNamesVisitor(D0ExpVisitor[frozenset[dvar]]):
    """Collect every variable occurrence and every binder name."""

    def visit_int(self, dexp: D0Eint) -> frozenset[dvar]:
        return frozenset()

    def visit_btf(self, dexp: D0Ebtf) -> frozenset[dvar]:
        return frozenset()

    def visit_var(self, dexp: D0Evar) -> frozenset[dvar]:
        return frozenset({dexp.arg1})

    def visit_op1(self, dexp: D0Eop1) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_op2(self, dexp: D0Eop2) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_lam(self, dexp: D0Elam) -> frozenset[dvar]:
        return dexp.arg2.accept(self) | {dexp.arg1}

    def visit_fix(self, dexp: D0Efix) -> frozenset[dvar]:
        return dexp.arg3.accept(self) | {dexp.arg1, dexp.arg2}

    def visit_app(self, dexp: D0Eapp) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_if0(self, dexp: D0Eif0) -> frozenset[dvar]:
        return (dexp.arg1.accept(self) | dexp.arg2.accept(self)
                | dexp.arg3.accept(self))

    def visit_let(self, dexp: D0Elet) -> frozenset[dvar]:
        return dexp.arg2.accept(self) | dexp.arg3.accept(self) | {dexp.arg1}

    def visit_pair(self, dexp: D0Epair) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_pfst(self, dexp: D0Epfst) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_psnd(self, dexp: D0Epsnd) -> frozenset[dvar]:
        return dexp.arg1.accept(self)


def d0exp_names(dexp: d0exp) -> frozenset[dvar]:
    """Return all variable and binder names occurring in an expression."""
    return dexp.accept(AllNamesVisitor())


########################################################################
# Task 2: capture-avoiding substitution
########################################################################

class FreshNames:
    """Deterministic fresh-name supply for one substitution call.

    Policy: to rename binder ``y``, try ``y_1``, ``y_2``, ... and take the
    first candidate not in ``used``. ``used`` starts as every name in the
    original expression and the replacement plus the target, and each
    generated name is added to it, so no two generated names coincide.
    """

    def __init__(self, used: frozenset[dvar] | set[dvar]) -> None:
        self.used: set[dvar] = set(used)

    def fresh(self, base: dvar) -> dvar:
        k = 1
        while f"{base}_{k}" in self.used:
            k += 1
        name = f"{base}_{k}"
        self.used.add(name)
        return name


class SubstitutionVisitor(D0ExpVisitor[d0exp]):
    """Apply a substitution ``sigma`` (name -> expression) to an expression.

    A call ``e[x := r]`` starts with ``sigma = {x: r}``. When a binder must be
    alpha-renamed from ``y`` to ``y'``, the body is visited with the extra
    entry ``y -> y'``, so the target replacement and the renaming happen in a
    single pass. Entering a binder makes a new visitor with an adjusted
    ``sigma``; ``self`` is never modified, so sibling scopes cannot leak.
    The fresh-name supply is shared by all visitors in one call.
    """

    def __init__(self, sigma: dict[dvar, d0exp], fresh: FreshNames,
                 range_fvs: dict[dvar, frozenset[dvar]] | None = None) -> None:
        self.sigma = sigma
        self.fresh = fresh
        # Free variables of each replacement, cached so binders can test capture.
        self.range_fvs = range_fvs if range_fvs is not None else {
            v: d0exp_fvset(e) for v, e in sigma.items()}

    def _enter(self, binders: list[dvar], body: d0exp) -> tuple[list[dvar], SubstitutionVisitor]:
        """Handle binders that scope over ``body``.

        Returns the (possibly renamed) binder names, in order, and the visitor
        to use for ``body``. ``binders`` are listed outermost first, so a later
        binder with the same name shadows an earlier one, as in the evaluator.
        """
        # Binders shadow any substitution for the same name.
        sigma = {v: e for v, e in self.sigma.items() if v not in binders}
        # Only entries whose name is actually free in the body can fire here.
        body_fv = d0exp_fvset(body)
        live = {v for v in sigma if v in body_fv}
        if not live:
            # Nothing to substitute in this scope: no renaming, keep binders.
            return list(binders), SubstitutionVisitor({}, self.fresh, {})
        danger = frozenset().union(*(self.range_fvs[v] for v in live))
        range_fvs = {v: self.range_fvs[v] for v in live}
        sigma = {v: sigma[v] for v in live}
        renamed: dict[dvar, dvar] = {}
        for b in binders:
            if b in danger and b not in renamed:
                renamed[b] = self.fresh.fresh(b)
        for old, new in renamed.items():
            sigma[old] = D0Evar(new)
            range_fvs[old] = frozenset({new})
        new_binders = [renamed.get(b, b) for b in binders]
        return new_binders, SubstitutionVisitor(sigma, self.fresh, range_fvs)

    def visit_int(self, dexp: D0Eint) -> d0exp:
        return D0Eint(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> d0exp:
        return D0Ebtf(dexp.arg1)

    def visit_var(self, dexp: D0Evar) -> d0exp:
        if dexp.arg1 in self.sigma:
            return self.sigma[dexp.arg1]
        return D0Evar(dexp.arg1)

    def visit_op1(self, dexp: D0Eop1) -> d0exp:
        return D0Eop1(dexp.name, dexp.arg1.accept(self))

    def visit_op2(self, dexp: D0Eop2) -> d0exp:
        return D0Eop2(dexp.name, dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_lam(self, dexp: D0Elam) -> d0exp:
        (x,), inner = self._enter([dexp.arg1], dexp.arg2)
        return D0Elam(x, dexp.arg2.accept(inner))

    def visit_fix(self, dexp: D0Efix) -> d0exp:
        # f is bound first, then x; if f == x the parameter shadows f, and
        # both get the same new name so that shadowing is preserved.
        (f, x), inner = self._enter([dexp.arg1, dexp.arg2], dexp.arg3)
        return D0Efix(f, x, dexp.arg3.accept(inner))

    def visit_app(self, dexp: D0Eapp) -> d0exp:
        return D0Eapp(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_if0(self, dexp: D0Eif0) -> d0exp:
        return D0Eif0(dexp.arg1.accept(self), dexp.arg2.accept(self),
                      dexp.arg3.accept(self))

    def visit_let(self, dexp: D0Elet) -> d0exp:
        # The initializer is outside the let's scope: substitute there with
        # the current visitor, even if the let-bound name equals the target.
        init = dexp.arg2.accept(self)
        (x,), inner = self._enter([dexp.arg1], dexp.arg3)
        return D0Elet(x, init, dexp.arg3.accept(inner))

    def visit_pair(self, dexp: D0Epair) -> d0exp:
        return D0Epair(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_pfst(self, dexp: D0Epfst) -> d0exp:
        return D0Epfst(dexp.arg1.accept(self))

    def visit_psnd(self, dexp: D0Epsnd) -> d0exp:
        return D0Epsnd(dexp.arg1.accept(self))


def d0exp_substitute(dexp: d0exp, dvar: dvar, replacement: d0exp) -> d0exp:
    """Return ``dexp[dvar := replacement]``, renaming binders to avoid capture.

    Neither input is mutated and nothing is evaluated. The replacement object
    is inserted as-is (it is shared, not copied) at each free occurrence.
    """
    used = d0exp_names(dexp) | d0exp_names(replacement) | {dvar}
    visitor = SubstitutionVisitor({dvar: replacement}, FreshNames(used))
    return dexp.accept(visitor)
