"""Church encodings, built as closed target terms.

Every combinator here is a closed ``Term`` made only of Var, Lam, and App.
Names such as TRUE, PAIR, and Z are just Python names for these terms; they
are not primitives of the target language. Putting one into a compiled
program places the whole pure term there.

Because every combinator is closed, its internal binder names (s, z, t, f, ...)
can never capture anything: the compiler only ever *applies* combinators to
translated subterms, it never wraps a translated subterm in one of these
binders. So those names stay free for source programs to use.

Encoding references: Church's numerals and booleans and the pair-based
predecessor follow Pierce, *Types and Programming Languages*, ch. 5, and the
Wikipedia article "Church encoding". The call-by-value fixed-point
combinator Z is the one given in Assign06.md.

Python arithmetic is used in exactly one place: ``NUM(n)`` builds the numeral
for a source literal by writing ``s`` n times. Everything a program computes
is done by beta reduction of the terms below.
"""
from __future__ import annotations

from target import App, Lam, Term, Var

__all__ = [
    "lams", "apps",
    "TRUE", "FALSE", "I", "NUM", "ZERO", "ONE",
    "SUCC", "PRED", "IS_ZERO", "ADD", "SUB", "MUL",
    "NOT", "AND", "OR",
    "LEQ", "LT", "GEQ", "GT", "EQ", "NEQ",
    "PAIR", "FST", "SND", "Z",
    "LIBRARY",
]


def lams(*params_and_body: str | Term) -> Term:
    """``lams("a", "b", body)`` is ``lam a. lam b. body``."""
    *params, body = params_and_body
    for p in reversed(params):
        body = Lam(p, body)
    return body


def apps(fn: Term, *args: Term) -> Term:
    """``apps(f, a, b)`` is ``((f a) b)`` (application associates left)."""
    for a in args:
        fn = App(fn, a)
    return fn


v = Var

########################################################################
# Booleans, identity, pairs
########################################################################

TRUE = lams("t", "f", v("t"))                       # lam t. lam f. t
FALSE = lams("t", "f", v("f"))                      # lam t. lam f. f
I = lams("w", v("w"))                               # lam w. w  (dummy value)

PAIR = lams("a", "b", "p", apps(v("p"), v("a"), v("b")))   # lam a. lam b. lam p. p a b
FST = lams("p", apps(v("p"), TRUE))                 # lam p. p TRUE
SND = lams("p", apps(v("p"), FALSE))                # lam p. p FALSE

# Strict boolean operators on boolean *values*. The compiler does not use
# AND/OR for source `and`/`or` (those must short-circuit, see compiler.py);
# they are used inside EQ and are part of the library for completeness.
NOT = lams("b", apps(v("b"), FALSE, TRUE))          # lam b. b FALSE TRUE
AND = lams("p", "q", apps(v("p"), v("q"), FALSE))   # lam p. lam q. p q FALSE
OR = lams("p", "q", apps(v("p"), TRUE, v("q")))     # lam p. lam q. p TRUE q

########################################################################
# Natural numbers
########################################################################


def NUM(n: int) -> Term:
    """Church numeral: lam s. lam z. s (s (... (s z)))  with n copies of s."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError(f"NUM expects a natural number, got {n!r}")
    body: Term = v("z")
    for _ in range(n):
        body = App(v("s"), body)
    return lams("s", "z", body)


ZERO = NUM(0)
ONE = NUM(1)

# lam n. lam s. lam z. s (n s z)
SUCC = lams("n", "s", "z", apps(v("s"), apps(v("n"), v("s"), v("z"))))

# Predecessor (Kleene's pair trick). Start from (0, 0) and apply
#     STEP = lam q. PAIR (SND q) (SUCC (SND q))       i.e. (a, b) |-> (b, b + 1)
# n times. After k steps the pair is (k - 1, k) for k >= 1, and (0, 0) for
# k = 0, so the first component is n - 1, or 0 when n = 0.
_PRED_STEP = lams("q", apps(PAIR, apps(SND, v("q")), apps(SUCC, apps(SND, v("q")))))
# lam n. FST (n STEP (PAIR ZERO ZERO))
PRED = lams("n", apps(FST, apps(v("n"), _PRED_STEP, apps(PAIR, ZERO, ZERO))))

# lam n. n (lam x. FALSE) TRUE
IS_ZERO = lams("n", apps(v("n"), lams("x", FALSE), TRUE))

# lam m. lam n. lam s. lam z. m s (n s z)
ADD = lams("m", "n", "s", "z", apps(v("m"), v("s"), apps(v("n"), v("s"), v("z"))))

# Truncated subtraction: apply PRED to m, n times.  lam m. lam n. n PRED m
SUB = lams("m", "n", apps(v("n"), PRED, v("m")))

# lam m. lam n. lam s. m (n s)
MUL = lams("m", "n", "s", apps(v("m"), apps(v("n"), v("s"))))

########################################################################
# Comparisons (all take two numeral values and return a boolean)
########################################################################

# m <= n  iff  m - n = 0   (truncated subtraction)
LEQ = lams("m", "n", apps(IS_ZERO, apps(SUB, v("m"), v("n"))))
# m >= n  iff  n <= m
GEQ = lams("m", "n", apps(LEQ, v("n"), v("m")))
# m < n   iff  not (n <= m)
LT = lams("m", "n", apps(NOT, apps(LEQ, v("n"), v("m"))))
# m > n   iff  not (m <= n)
GT = lams("m", "n", apps(NOT, apps(LEQ, v("m"), v("n"))))
# m == n  iff  m <= n and n <= m
EQ = lams("m", "n", apps(AND, apps(LEQ, v("m"), v("n")), apps(LEQ, v("n"), v("m"))))
# m != n  iff  not (m == n)
NEQ = lams("m", "n", apps(NOT, apps(EQ, v("m"), v("n"))))

########################################################################
# Call-by-value fixed-point combinator
########################################################################

# Z = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
# The eta-expansion `lam v. x x v` is a value, so CBV stops there instead of
# unfolding `x x` forever the way the ordinary Y combinator would.
_Z_HALF = lams("x", apps(v("g"), lams("v", apps(v("x"), v("x"), v("v")))))
Z = lams("g", apps(_Z_HALF, _Z_HALF))

# Everything above, by name, for the closedness test and documentation.
LIBRARY: dict[str, Term] = {
    "TRUE": TRUE, "FALSE": FALSE, "I": I,
    "PAIR": PAIR, "FST": FST, "SND": SND,
    "NOT": NOT, "AND": AND, "OR": OR,
    "ZERO": ZERO, "ONE": ONE, "SUCC": SUCC, "PRED": PRED, "IS_ZERO": IS_ZERO,
    "ADD": ADD, "SUB": SUB, "MUL": MUL,
    "LEQ": LEQ, "GEQ": GEQ, "LT": LT, "GT": GT, "EQ": EQ, "NEQ": NEQ,
    "Z": Z,
}
