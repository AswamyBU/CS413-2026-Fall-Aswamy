"""Source programs used by the demonstration and the tests.

Programs are built directly as source ASTs (no parser). ``EXAMPLES`` holds
the fourteen mandatory demonstrations (DEMO-01 .. DEMO-14, numbered as in
REQUIREMENTS.md section 7.1) followed by a few extra checks (EXTRA-*).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from observe import BOOL, NAT, pair_kind
from source_syntax import (
    D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar, d0exp,
)

EXHAUSTION = "budget exhaustion"   # expected outcome for divergent programs


# Small constructors so the programs below read close to the notation.
def num(n: int) -> d0exp: return D0Eint(n)
def var(x: str) -> d0exp: return D0Evar(x)
def lam(x: str, body: d0exp) -> d0exp: return D0Elam(x, body)
def app(f: d0exp, a: d0exp) -> d0exp: return D0Eapp(f, a)
def op(name: str, a: d0exp, b: d0exp) -> d0exp: return D0Eop2(name, a, b)
def if_(c: d0exp, t: d0exp, f: d0exp) -> d0exp: return D0Eif0(c, t, f)
def let(x: str, init: d0exp, body: d0exp) -> d0exp: return D0Elet(x, init, body)
def pair(a: d0exp, b: d0exp) -> d0exp: return D0Epair(a, b)


TRUE_ = D0Ebtf(True)
FALSE_ = D0Ebtf(False)


def LOOP() -> d0exp:
    """(fix loop(x). loop x) 0 -- diverges."""
    return app(D0Efix("loop", "x", app(var("loop"), var("x"))), num(0))


def FACT() -> d0exp:
    """fix fact(n). if n == 0 then 1 else n * fact (n - 1)"""
    n, fact = var("n"), var("fact")
    return D0Efix("fact", "n",
                  if_(op("==", n, num(0)),
                      num(1),
                      op("*", n, app(fact, op("-", n, num(1))))))


def FIB() -> d0exp:
    """fix fib(n). if n < 2 then n else fib (n - 1) + fib (n - 2)"""
    n, fib = var("n"), var("fib")
    return D0Efix("fib", "n",
                  if_(op("<", n, num(2)),
                      n,
                      op("+", app(fib, op("-", n, num(1))),
                              app(fib, op("-", n, num(2))))))


@dataclass(frozen=True)
class Example:
    ident: str
    notation: str          # explanatory notation from the assignment
    source: d0exp
    kind: Any              # NAT, BOOL, or pair_kind(...)
    expected: Any          # Python value, or EXHAUSTION
    mandatory: bool = True

    @property
    def diverges(self) -> bool:
        return self.expected == EXHAUSTION


EXAMPLES: list[Example] = [
    Example("DEMO-01", "2 + 3 * 4",
            op("+", num(2), op("*", num(3), num(4))), NAT, 14),
    Example("DEMO-02", "2 - 5", op("-", num(2), num(5)), NAT, 0),
    Example("DEMO-03", "if 2 <= 3 then 7 else 9",
            if_(op("<=", num(2), num(3)), num(7), num(9)), NAT, 7),
    Example("DEMO-04", "let x = 3 in (lam y. x + y) 4",
            let("x", num(3), app(lam("y", op("+", var("x"), var("y"))), num(4))),
            NAT, 7),
    Example("DEMO-05", "fst (pair 2 true)", D0Epfst(pair(num(2), TRUE_)), NAT, 2),
    Example("DEMO-06", "snd (pair 2 true)", D0Epsnd(pair(num(2), TRUE_)), BOOL, True),
    Example("DEMO-07", "(lam f. f 3) (lam x. x + 1)",
            app(lam("f", app(var("f"), num(3))), lam("x", op("+", var("x"), num(1)))),
            NAT, 4),
    Example("DEMO-08", "if true then 1 else LOOP", if_(TRUE_, num(1), LOOP()), NAT, 1),
    Example("DEMO-09", "(lam x. 0) LOOP", app(lam("x", num(0)), LOOP()),
            NAT, EXHAUSTION),
    Example("DEMO-10", "fact 4   where fact = fix fact(n). if n == 0 then 1 else n * fact (n - 1)",
            app(FACT(), num(4)), NAT, 24),
    Example("DEMO-11", "fib 5    where fib = fix fib(n). if n < 2 then n else fib (n - 1) + fib (n - 2)",
            app(FIB(), num(5)), NAT, 5),
    Example("DEMO-12", "LOOP = (fix loop(x). loop x) 0", LOOP(), NAT, EXHAUSTION),
    Example("DEMO-13", "true and false", op("and", TRUE_, FALSE_), BOOL, False),
    Example("DEMO-14", "false or true", op("or", FALSE_, TRUE_), BOOL, True),
    # Extra demonstrations (not in the required table).
    Example("EXTRA-1", "pair (pair 2 true) 3",
            pair(pair(num(2), TRUE_), num(3)),
            pair_kind(pair_kind(NAT, BOOL), NAT), ((2, True), 3), mandatory=False),
    Example("EXTRA-2", "(fix f(f). f) 3   (coincident fix binders)",
            app(D0Efix("f", "f", var("f")), num(3)), NAT, 3, mandatory=False),
    Example("EXTRA-3", "false and LOOP   (short-circuit)",
            op("and", FALSE_, LOOP()), BOOL, False, mandatory=False),
    Example("EXTRA-4", "true or LOOP   (short-circuit)",
            op("or", TRUE_, LOOP()), BOOL, True, mandatory=False),
    Example("EXTRA-5", "let x = LOOP in 2", let("x", LOOP(), num(2)),
            NAT, EXHAUSTION, mandatory=False),
    Example("EXTRA-6", "not (3 != 3)", D0Eop1("not", op("!=", num(3), num(3))),
            BOOL, True, mandatory=False),
]
