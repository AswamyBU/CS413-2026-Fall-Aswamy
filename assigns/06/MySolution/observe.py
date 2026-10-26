"""Bounded observers that decode target values into Python data.

The caller always says what kind of result it expects, because NUM(0) and
FALSE are the same lambda term. A kind is one of

    NAT                      a Church natural
    BOOL                     a Church boolean
    pair_kind(k1, k2)        a Church pair whose components have kinds k1, k2

Observation contexts (pure target terms, run by the shared evaluator):

    natural:  n STEP BASE     STEP = lam tail. lam c. lam z. c tail
                              BASE = lam c. lam z. z
              Call-by-value turns n's s-applications into a finite spine
                  lam c. lam z. c (lam c. lam z. c (... (lam c. lam z. z)))
              whose nodes Python counts, up to alpha-renaming.
    boolean:  b MARK_T MARK_F with distinct closed markers
                  MARK_T = lam p. lam q. lam r. p
                  MARK_F = lam p. lam q. lam r. q
              Python checks which marker came back (alpha-equivalence).
    pair:     FST p and SND p are evaluated under the budget, then each
              component is observed with its own kind (recursively).

Python only inspects the *final* shape. It never evaluates under a lambda
and never does the program's arithmetic.

Every observer returns an ``Observation``. ``status`` is ``"ok"`` (``value``
holds the decoded int/bool/tuple), ``"exhausted"`` (the observation budget
ran out; nothing is decoded), or ``"malformed"`` (the context finished but the
result was not the expected shape; ``detail`` says why). ``steps`` counts the
beta-value steps used by the observation, separately from execution.
For a pair, ``budget`` is shared by the whole observation (projections and
all nested component observations).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from church import FST, SND, apps, lams
from evaluator import evaluate
from target import App, Lam, Term, Var, alpha_equiv, show

__all__ = [
    "NAT", "BOOL", "pair_kind", "kind_name",
    "STEP", "BASE", "MARK_TRUE", "MARK_FALSE",
    "Observation", "OK", "OBS_EXHAUSTED", "MALFORMED",
    "observe", "observe_nat", "observe_bool", "observe_pair",
]

NAT = "nat"
BOOL = "bool"


def pair_kind(first, second) -> tuple:
    return ("pair", first, second)


def kind_name(kind) -> str:
    if isinstance(kind, tuple):
        return f"pair({kind_name(kind[1])}, {kind_name(kind[2])})"
    return kind


OK = "ok"
OBS_EXHAUSTED = "exhausted"
MALFORMED = "malformed"


@dataclass(frozen=True)
class Observation:
    status: str
    value: Any
    steps: int
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == OK


STEP = lams("tail", "c", "z", App(Var("c"), Var("tail")))
BASE = lams("c", "z", Var("z"))
MARK_TRUE = lams("p", "q", "r", Var("p"))
MARK_FALSE = lams("p", "q", "r", Var("q"))


def _remaining(budget: int | None, used: int) -> int | None:
    return None if budget is None else budget - used


def observe_nat(value: Term, budget: int | None) -> Observation:
    result = evaluate(apps(value, STEP, BASE), budget)
    if not result.completed:
        return Observation(OBS_EXHAUSTED, None, result.steps,
                           "observation budget exhausted")
    count, t = 0, result.value
    while True:     # iterative, so long spines are fine
        match t:
            case Lam(c, Lam(z, App(Var(head), tail))) if head == c and c != z:
                count += 1
                t = tail
            case Lam(_, Lam(z, Var(last))) if last == z:
                return Observation(OK, count, result.steps)
            case _:
                return Observation(MALFORMED, None, result.steps,
                                   f"not a numeral spine: {_clip(show(t))}")


def observe_bool(value: Term, budget: int | None) -> Observation:
    result = evaluate(apps(value, MARK_TRUE, MARK_FALSE), budget)
    if not result.completed:
        return Observation(OBS_EXHAUSTED, None, result.steps,
                           "observation budget exhausted")
    if alpha_equiv(result.value, MARK_TRUE):
        return Observation(OK, True, result.steps)
    if alpha_equiv(result.value, MARK_FALSE):
        return Observation(OK, False, result.steps)
    return Observation(MALFORMED, None, result.steps,
                       f"neither boolean marker: {_clip(show(result.value))}")


def observe_pair(value: Term, first_kind, second_kind,
                 budget: int | None) -> Observation:
    used = 0
    parts = []
    for proj, kind in ((FST, first_kind), (SND, second_kind)):
        projected = evaluate(App(proj, value), _remaining(budget, used))
        used += projected.steps
        if not projected.completed:
            return Observation(OBS_EXHAUSTED, None, used,
                               "observation budget exhausted in a projection")
        part = observe(projected.value, kind, _remaining(budget, used))
        used += part.steps
        if not part.ok:
            return Observation(part.status, None, used, part.detail)
        parts.append(part.value)
    return Observation(OK, tuple(parts), used)


def observe(value: Term, kind, budget: int | None) -> Observation:
    """Decode ``value`` (a target value) as ``kind`` within ``budget`` steps."""
    if kind == NAT:
        return observe_nat(value, budget)
    if kind == BOOL:
        return observe_bool(value, budget)
    if isinstance(kind, tuple) and len(kind) == 3 and kind[0] == "pair":
        return observe_pair(value, kind[1], kind[2], budget)
    raise ValueError(f"unknown result kind {kind!r}")


def _clip(text: str, width: int = 120) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."
