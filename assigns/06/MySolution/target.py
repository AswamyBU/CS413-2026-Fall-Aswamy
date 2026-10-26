"""Target language: Church's pure, untyped lambda-calculus.

    Term ::= Var(name) | Lam(name, Term) | App(Term, Term)

This module defines the target AST and the operations on it that do not
evaluate anything: printing, free variables, all names, capture-avoiding
substitution, alpha-equivalence, and a purity check.

The three classes use the same field layout as the matching source classes
(``D0Evar(arg1)``, ``D0Elam(arg1, arg2)``, ``D0Eapp(arg1, arg2)``) and the same
``accept``/``visit_var``/``visit_lam``/``visit_app`` protocol. That is what lets
the single shared evaluator in ``evaluator.py`` handle variables, lambdas, and
applications of both languages with one set of methods. Readable aliases
(``name``, ``param``, ``body``, ``fn``, ``arg``) are provided as properties.

Terms are immutable (frozen dataclasses). Free variables and all names are
computed once per node and cached, so substitution can skip any subterm in
which the target variable is not free and share it instead of copying it.

The fresh-name policy for alpha-renaming in ``substitute`` is adapted from my
Assignment 5 ``FreshNames`` class (assigns/05/MySolution/lambda1_visitors.py).

Requires Python 3.12 or later.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property

__all__ = [
    "Term", "Var", "Lam", "App",
    "IDENT_RE", "is_identifier",
    "show", "free_vars", "all_names", "substitute", "alpha_equiv",
    "is_pure", "term_size", "fresh_name",
]

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def is_identifier(name: object) -> bool:
    """True when ``name`` follows the Assignment 5 identifier convention."""
    return isinstance(name, str) and IDENT_RE.fullmatch(name) is not None


########################################################################
# The target AST
########################################################################

class Term:
    """Base class of the three target forms. Never instantiated directly."""

    @cached_property
    def fv(self) -> frozenset[str]:
        """Free variables of this term (cached per node)."""
        match self:
            case Var(x):
                return frozenset((x,))
            case Lam(x, body):
                return body.fv - {x}
            case App(fn, arg):
                return fn.fv | arg.fv
        raise TypeError(f"not a target term: {self!r}")

    @cached_property
    def names(self) -> frozenset[str]:
        """Every name in this term: free, bound, and binder names (cached)."""
        match self:
            case Var(x):
                return frozenset((x,))
            case Lam(x, body):
                return body.names | {x}
            case App(fn, arg):
                return fn.names | arg.names
        raise TypeError(f"not a target term: {self!r}")

    def __str__(self) -> str:
        return show(self)


@dataclass(frozen=True, repr=False)
class Var(Term):
    arg1: str

    @property
    def name(self) -> str:
        return self.arg1

    def accept(self, visitor):
        return visitor.visit_var(self)

    def __repr__(self) -> str:
        return f"Var({self.arg1!r})"


@dataclass(frozen=True, repr=False)
class Lam(Term):
    arg1: str
    arg2: Term

    @property
    def param(self) -> str:
        return self.arg1

    @property
    def body(self) -> Term:
        return self.arg2

    def accept(self, visitor):
        return visitor.visit_lam(self)

    def __repr__(self) -> str:
        return f"Lam({self.arg1!r}, {self.arg2!r})"


@dataclass(frozen=True, repr=False)
class App(Term):
    arg1: Term
    arg2: Term

    @property
    def fn(self) -> Term:
        return self.arg1

    @property
    def arg(self) -> Term:
        return self.arg2

    def accept(self, visitor):
        return visitor.visit_app(self)

    def __repr__(self) -> str:
        return f"App({self.arg1!r}, {self.arg2!r})"


########################################################################
# Printing
########################################################################

def show(term: Term) -> str:
    """Print ``x``, ``(lam x. body)``, and ``(fn arg)``, recursively."""
    out: list[str] = []
    # Explicit stack so that long spines do not hit the recursion limit.
    stack: list[Term | str] = [term]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, Var):
            out.append(item.arg1)
        elif isinstance(item, Lam):
            out.append(f"(lam {item.arg1}. ")
            stack.append(")")
            stack.append(item.arg2)
        elif isinstance(item, App):
            out.append("(")
            stack.append(")")
            stack.append(item.arg2)
            stack.append(" ")
            stack.append(item.arg1)
        else:
            raise TypeError(f"not a target term: {item!r}")
    return "".join(out)


########################################################################
# Names
########################################################################

def free_vars(term: Term) -> frozenset[str]:
    return term.fv


def all_names(term: Term) -> frozenset[str]:
    return term.names


def fresh_name(base: str, avoid: frozenset[str] | set[str]) -> str:
    """Deterministic fresh name: ``base`` itself if unused, else the first of
    ``base_1``, ``base_2``, ... that is not in ``avoid``."""
    if base not in avoid:
        return base
    k = 1
    while f"{base}_{k}" in avoid:
        k += 1
    return f"{base}_{k}"


########################################################################
# Capture-avoiding substitution
########################################################################

class _FreshSupply:
    """Fresh names for one substitution call (Assignment 5 policy).

    To rename binder ``y`` try ``y_1``, ``y_2``, ... and take the first name
    not used anywhere in the original term, the replacement, the target
    variable, or an earlier generated name. The used set is built lazily,
    because most substitutions (all of them, when evaluating closed terms)
    never need to rename anything.
    """

    def __init__(self, term: Term, name: str, replacement: Term) -> None:
        self._seed = (term, name, replacement)
        self._used: set[str] | None = None

    def fresh(self, base: str) -> str:
        if self._used is None:
            term, name, replacement = self._seed
            self._used = set(term.names | replacement.names | {name})
        k = 1
        while f"{base}_{k}" in self._used:
            k += 1
        new = f"{base}_{k}"
        self._used.add(new)
        return new


def substitute(term: Term, name: str, replacement: Term) -> Term:
    """Return ``term[name := replacement]`` without capturing free variables.

    Works on open terms. Neither input is mutated; unchanged subterms are
    shared with the input rather than copied.
    """
    if name not in term.fv:
        return term
    return _subst(term, name, replacement, replacement.fv,
                  _FreshSupply(term, name, replacement))


def _subst(t: Term, x: str, r: Term, rfv: frozenset[str],
           fresh: _FreshSupply) -> Term:
    if x not in t.fv:
        return t
    if isinstance(t, Var):          # x is free in t, so t is exactly x
        return r
    if isinstance(t, App):
        return App(_subst(t.arg1, x, r, rfv, fresh),
                   _subst(t.arg2, x, r, rfv, fresh))
    # Lam: x is free in t, so the binder is not x.
    y, body = t.arg1, t.arg2
    if y in rfv:
        # The binder would capture a free variable of r: rename it first.
        y_new = fresh.fresh(y)
        body = _subst(body, y, Var(y_new), frozenset((y_new,)), fresh)
        y = y_new
    return Lam(y, _subst(body, x, r, rfv, fresh))


########################################################################
# Alpha-equivalence, purity, size
########################################################################

def alpha_equiv(a: Term, b: Term) -> bool:
    """True when ``a`` and ``b`` differ only by consistent renaming of
    bound variables."""
    # Each environment maps a name to the depth of its innermost binder.
    stack = [(a, b, {}, {}, 0)]
    while stack:
        s, t, env_s, env_t, depth = stack.pop()
        if isinstance(s, Var) and isinstance(t, Var):
            ds, dt = env_s.get(s.arg1), env_t.get(t.arg1)
            if ds is None and dt is None:
                if s.arg1 != t.arg1:
                    return False
            elif ds != dt:
                return False
        elif isinstance(s, Lam) and isinstance(t, Lam):
            stack.append((s.arg2, t.arg2,
                          {**env_s, s.arg1: depth}, {**env_t, t.arg1: depth},
                          depth + 1))
        elif isinstance(s, App) and isinstance(t, App):
            stack.append((s.arg1, t.arg1, env_s, env_t, depth))
            stack.append((s.arg2, t.arg2, env_s, env_t, depth))
        else:
            return False
    return True


def is_pure(term: object) -> bool:
    """True when every node is exactly Var, Lam, or App and every name is a
    valid identifier."""
    stack = [term]
    while stack:
        t = stack.pop()
        kind = type(t)
        if kind is Var:
            if not is_identifier(t.arg1):
                return False
        elif kind is Lam:
            if not is_identifier(t.arg1):
                return False
            stack.append(t.arg2)
        elif kind is App:
            stack.append(t.arg1)
            stack.append(t.arg2)
        else:
            return False
    return True


def term_size(term: Term) -> int:
    """Number of AST nodes (shared subterms counted at every occurrence)."""
    n = 0
    stack = [term]
    while stack:
        t = stack.pop()
        n += 1
        if isinstance(t, Lam):
            stack.append(t.arg2)
        elif isinstance(t, App):
            stack.append(t.arg1)
            stack.append(t.arg2)
    return n
