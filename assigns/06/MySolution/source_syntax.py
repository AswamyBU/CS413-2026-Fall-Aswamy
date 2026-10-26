"""Source-language helpers: import of the supplied AST, printing, substitution.

The source AST and ``D0ExpVisitor`` come unchanged from
``assigns/05/lambda1_vp.py``; this module puts that directory on ``sys.path``
and re-exports what the rest of the project needs.

ATTRIBUTION: ``PrettyPrintVisitor``, ``AllNamesVisitor``, ``FreshNames`` and
``SubstitutionVisitor`` are adapted from my own Assignment 5 solution
(``assigns/05/MySolution/lambda1_visitors.py``). The changes are small: the
printer and substitution are unchanged in behaviour, and
``source_value_to_python`` is new.

Requires Python 3.12 or later.
"""
from __future__ import annotations

import sys
from pathlib import Path

# lambda1_vp.py lives in assigns/05; this file is in assigns/06/MySolution.
_A05 = str(Path(__file__).resolve().parent.parent.parent / "05")
if _A05 not in sys.path:
    sys.path.insert(0, _A05)

from lambda1_vp import (  # noqa: E402
    D0E000, D0ExpVisitor, d0exp, dvar, d0exp_fvset,
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar, D0Elam, D0Efix,
    D0Eapp, D0Eif0, D0Elet, D0Epair, D0Epfst, D0Epsnd,
)

__all__ = [
    "D0E000", "D0ExpVisitor", "d0exp", "dvar", "d0exp_fvset",
    "D0Eint", "D0Ebtf", "D0Eop1", "D0Eop2", "D0Evar", "D0Elam", "D0Efix",
    "D0Eapp", "D0Eif0", "D0Elet", "D0Epair", "D0Epfst", "D0Epsnd",
    "pretty", "source_names", "source_substitute", "source_value_to_python",
]


########################################################################
# Printing (from Assignment 5)
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


def pretty(dexp: d0exp) -> str:
    """Pretty-print a source expression without evaluating it."""
    return dexp.accept(PrettyPrintVisitor())


########################################################################
# All names (from Assignment 5)
########################################################################

class AllNamesVisitor(D0ExpVisitor[frozenset[dvar]]):
    """Collect every variable occurrence and every binder name."""

    def visit_int(self, dexp): return frozenset()
    def visit_btf(self, dexp): return frozenset()
    def visit_var(self, dexp): return frozenset({dexp.arg1})
    def visit_op1(self, dexp): return dexp.arg1.accept(self)
    def visit_op2(self, dexp): return dexp.arg1.accept(self) | dexp.arg2.accept(self)
    def visit_lam(self, dexp): return dexp.arg2.accept(self) | {dexp.arg1}
    def visit_fix(self, dexp): return dexp.arg3.accept(self) | {dexp.arg1, dexp.arg2}
    def visit_app(self, dexp): return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_if0(self, dexp):
        return (dexp.arg1.accept(self) | dexp.arg2.accept(self)
                | dexp.arg3.accept(self))

    def visit_let(self, dexp):
        return dexp.arg2.accept(self) | dexp.arg3.accept(self) | {dexp.arg1}

    def visit_pair(self, dexp): return dexp.arg1.accept(self) | dexp.arg2.accept(self)
    def visit_pfst(self, dexp): return dexp.arg1.accept(self)
    def visit_psnd(self, dexp): return dexp.arg1.accept(self)


def source_names(dexp: d0exp) -> frozenset[dvar]:
    return dexp.accept(AllNamesVisitor())


########################################################################
# Capture-avoiding substitution on source ASTs (from Assignment 5)
########################################################################

class FreshNames:
    """Deterministic fresh names: try ``y_1``, ``y_2``, ... and take the first
    one not in ``used``; each generated name is then added to ``used``."""

    def __init__(self, used) -> None:
        self.used: set[dvar] = set(used)

    def fresh(self, base: dvar) -> dvar:
        k = 1
        while f"{base}_{k}" in self.used:
            k += 1
        name = f"{base}_{k}"
        self.used.add(name)
        return name


class SubstitutionVisitor(D0ExpVisitor[d0exp]):
    """Apply ``sigma`` (name -> expression), renaming binders to avoid capture.

    A binder makes a new visitor for its body, so changes never leak into
    sibling scopes or into a let initializer.
    """

    def __init__(self, sigma, fresh: FreshNames, range_fvs=None) -> None:
        self.sigma = sigma
        self.fresh = fresh
        self.range_fvs = range_fvs if range_fvs is not None else {
            x: d0exp_fvset(e) for x, e in sigma.items()}

    def _enter(self, binders, body):
        sigma = {x: e for x, e in self.sigma.items() if x not in binders}
        body_fv = d0exp_fvset(body)
        live = {x for x in sigma if x in body_fv}
        if not live:
            return list(binders), SubstitutionVisitor({}, self.fresh, {})
        danger = frozenset().union(*(self.range_fvs[x] for x in live))
        range_fvs = {x: self.range_fvs[x] for x in live}
        sigma = {x: sigma[x] for x in live}
        renamed: dict[dvar, dvar] = {}
        for b in binders:
            if b in danger and b not in renamed:
                renamed[b] = self.fresh.fresh(b)
        for old, new in renamed.items():
            sigma[old] = D0Evar(new)
            range_fvs[old] = frozenset({new})
        return ([renamed.get(b, b) for b in binders],
                SubstitutionVisitor(sigma, self.fresh, range_fvs))

    def visit_int(self, dexp): return dexp
    def visit_btf(self, dexp): return dexp

    def visit_var(self, dexp):
        return self.sigma.get(dexp.arg1, dexp)

    def visit_op1(self, dexp):
        return D0Eop1(dexp.name, dexp.arg1.accept(self))

    def visit_op2(self, dexp):
        return D0Eop2(dexp.name, dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_lam(self, dexp):
        (x,), inner = self._enter([dexp.arg1], dexp.arg2)
        return D0Elam(x, dexp.arg2.accept(inner))

    def visit_fix(self, dexp):
        # f first, then x; if f == x both get the same new name, so the
        # parameter still shadows the function name.
        (f, x), inner = self._enter([dexp.arg1, dexp.arg2], dexp.arg3)
        return D0Efix(f, x, dexp.arg3.accept(inner))

    def visit_app(self, dexp):
        return D0Eapp(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_if0(self, dexp):
        return D0Eif0(dexp.arg1.accept(self), dexp.arg2.accept(self),
                      dexp.arg3.accept(self))

    def visit_let(self, dexp):
        init = dexp.arg2.accept(self)   # initializer is outside the let's scope
        (x,), inner = self._enter([dexp.arg1], dexp.arg3)
        return D0Elet(x, init, dexp.arg3.accept(inner))

    def visit_pair(self, dexp):
        return D0Epair(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_pfst(self, dexp):
        return D0Epfst(dexp.arg1.accept(self))

    def visit_psnd(self, dexp):
        return D0Epsnd(dexp.arg1.accept(self))


def source_substitute(dexp: d0exp, name: dvar, replacement: d0exp) -> d0exp:
    """Return ``dexp[name := replacement]`` on source ASTs (no mutation)."""
    if name not in d0exp_fvset(dexp):
        return dexp
    used = source_names(dexp) | source_names(replacement) | {name}
    return dexp.accept(SubstitutionVisitor({name: replacement}, FreshNames(used)))


########################################################################
# Source values as Python data
########################################################################

def source_value_to_python(value: d0exp):
    """Turn a source value into Python data: int, bool, tuple, or the string
    ``"<function>"`` for a lambda or fix value."""
    if isinstance(value, D0Eint):
        return int(value.arg1)
    if isinstance(value, D0Ebtf):
        return bool(value.arg1)
    if isinstance(value, D0Epair):
        return (source_value_to_python(value.arg1),
                source_value_to_python(value.arg2))
    if isinstance(value, (D0Elam, D0Efix)):
        return "<function>"
    raise TypeError(f"not a source value: {value!r}")
