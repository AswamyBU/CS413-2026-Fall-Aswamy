"""The Eight Queens puzzle as a LAMBDA0 term.

Translation of the ATS2 program in ``queens.dats`` (Hongwei Xi's eight-queens
example, taken from assigns/01/MySolution) into a closed ``t0erm`` that is run
by ``t0erm_cbv_evaluate0`` from ``lambda0.py``.  All of the search and all of
the conflict checking happen inside the term; the Python code below only
*builds* ASTs and *decodes/prints* the values the interpreter returns.

Run:  python3 queens_lambda0.py          # count solutions for N = 8
      python3 queens_lambda0.py --all    # also print every solution

Representations (documented again in README.md)
-----------------------------------------------
* board   : the ATS ``int8`` tuple becomes a right-nested list of pairs
            ``(x0, (x1, (... (x_{n-1}, 0))))`` ended by ``T0Mint(0)``.
            ``x_k`` is the column of the queen in row ``k``; unset rows hold 0
            (as in the ATS program's initial board).
* boards  : (collecting mode only) a list of boards, same pair encoding.
* multi-argument functions are curried: ``f a b c`` is ``T0Mapp(T0Mapp(
            T0Mapp(f, a), b), c)``; recursive ones are ``T0Mfix`` whose body
            is a chain of ``T0Mlam``.
* ``let x = e in b`` is ``(lambda x. b) e``.
* ``andalso`` is ``if a then b else false``; ``abs`` is a small function.

The board size N is a parameter of the term (``lambda n. ...``) instead of the
ATS constant ``#define N 8`` so that smaller boards can be tested.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0,
    T0Mop1, T0Mop2, T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_cbv_evaluate0, t0erm_fvset,
)

########################################################################
# Small AST-building helpers (Python only builds terms; it never searches)
########################################################################

def V(x): return T0Mvar(x)
def I(n): return T0Mint(n)
def op2(o, a, b): return T0Mop2(o, a, b)
def cond(c, a, b): return T0Mif0(c, a, b)
def fst(t): return T0Mpfst(t)
def snd(t): return T0Mpsnd(t)
def pair(a, b): return T0Mpair(a, b)
def FALSE(): return T0Mbtf(False)
def TRUE(): return T0Mbtf(True)


def app(f, *args):
    """Curried application f a1 a2 ... an."""
    for a in args:
        f = T0Mapp(f, a)
    return f


def lam(params, body):
    """lambda p1. lambda p2. ... body"""
    for p in reversed(params):
        body = T0Mlam(p, body)
    return body


def fix(name, params, body):
    """A recursive curried function: fix name p1. lambda p2. ... body"""
    inner = lam(params[1:], body)
    return T0Mfix(name, params[0], inner)


def let(x, e, body):
    return T0Mapp(T0Mlam(x, body), e)


def andalso(a, b):
    return cond(a, b, FALSE())


########################################################################
# The translated ATS functions, each as a closed term
########################################################################

def abs_term():
    # abs = lambda x. if x < 0 then -x else x
    return lam(["x"], cond(op2("<", V("x"), I(0)), T0Mop1("-", V("x")), V("x")))


def board_get_term():
    # fun board_get (bd, i) = if i = 0 then bd.0 else ... (8-way test on the tuple)
    # Here: nth element of the pair-list.
    #   bget bd i = if i == 0 then fst bd else bget (snd bd) (i - 1)
    # Running off the end projects from an int and so raises TypeError
    # (the ATS version returned 0 for i outside 0..7).
    return fix("bget", ["bd", "i"],
        cond(op2("==", V("i"), I(0)),
             fst(V("bd")),
             app(V("bget"), snd(V("bd")), op2("-", V("i"), I(1)))))


def board_set_term():
    # bset bd i j = if i == 0 then (j, snd bd) else (fst bd, bset (snd bd) (i-1) j)
    return fix("bset", ["bd", "i", "j"],
        cond(op2("==", V("i"), I(0)),
             pair(V("j"), snd(V("bd"))),
             pair(fst(V("bd")),
                  app(V("bset"), snd(V("bd")), op2("-", V("i"), I(1)), V("j")))))


def safety_test1_term():
    # safety_test1 (i0, j0, i, j) = j0 <> j andalso abs (i0 - i) <> abs (j0 - j)
    body = andalso(
        op2("!=", V("j0"), V("j")),
        op2("!=",
            app(V("abs"), op2("-", V("i0"), V("i"))),
            app(V("abs"), op2("-", V("j0"), V("j")))))
    return let("abs", abs_term(), lam(["i0", "j0", "i", "j"], body))


def safety_test2_term():
    # safety_test2 (i0, j0, bd, i) =
    #   if i >= 0 then
    #     if safety_test1 (i0, j0, i, board_get (bd, i))
    #       then safety_test2 (i0, j0, bd, i-1) else false
    #   else true
    body = cond(
        op2(">=", V("i"), I(0)),
        cond(app(V("st1"), V("i0"), V("j0"), V("i"), app(V("bget"), V("bd"), V("i"))),
             app(V("st2"), V("i0"), V("j0"), V("bd"), op2("-", V("i"), I(1))),
             FALSE()),
        TRUE())
    return let("st1", safety_test1_term(),
           let("bget", board_get_term(),
               fix("st2", ["i0", "j0", "bd", "i"], body)))


def make_board_term():
    # A board of k rows, all unset (0):  mk k = if k == 0 then 0 else (0, mk (k-1))
    return fix("mk", ["k"],
        cond(op2("==", V("k"), I(0)),
             I(0),
             pair(I(0), app(V("mk"), op2("-", V("k"), I(1))))))


def search_term(collect):
    """The ATS ``search``, closed over n, safety_test2, board_get, board_set.

    ``acc`` plays the role of ATS's ``nsol``.  With ``collect=False`` it *is*
    the solution count (exactly as in the ATS program).  With ``collect=True``
    it is ``(count, boards)`` where ``boards`` is a list (nested pairs ended
    by 0) of the solution boards, newest first; ATS prints each board when
    found, and a term cannot print, so it accumulates them instead.
    """
    def add(acc, bd1):  # what "nsol+1 (and print the board)" becomes
        if collect:
            return pair(op2("+", fst(acc), I(1)), pair(bd1, snd(acc)))
        return op2("+", acc, I(1))

    bd, i, j, acc = V("bd"), V("i"), V("j"), V("acc")
    S = V("search")
    n = V("n")
    j_plus_1 = op2("+", j, I(1))

    on_safe = let("bd1", app(V("bset"), bd, i, j),
        cond(op2("==", op2("+", i, I(1)), n),
             # solution found: keep looking in the same row, at column j+1
             app(S, bd, i, j_plus_1, add(acc, V("bd1"))),
             # place the next queen
             app(S, V("bd1"), op2("+", i, I(1)), I(0), acc)))

    backtrack = cond(
        op2(">", i, I(0)),
        app(S, bd, op2("-", i, I(1)),
            op2("+", app(V("bget"), bd, op2("-", i, I(1))), I(1)), acc),
        acc)

    body = cond(
        op2("<", j, n),
        let("test", app(V("st2"), i, j, bd, op2("-", i, I(1))),
            cond(V("test"), on_safe, app(S, bd, i, j_plus_1, acc))),
        backtrack)

    return fix("search", ["bd", "i", "j", "acc"], body)


def queens_term(collect=False):
    """A closed term: lambda n. <search for n queens on an n x n board>.

    Applied to ``T0Mint(n)`` it returns the number of solutions (collect =
    False) or the pair (count, list-of-boards) (collect = True).
    """
    init_acc = pair(I(0), I(0)) if collect else I(0)
    body = app(V("search"), app(V("mk"), V("n")), I(0), I(0), init_acc)
    term = lam(["n"],
        let("bget", board_get_term(),
        let("bset", board_set_term(),
        let("st2", safety_test2_term(),
        let("mk", make_board_term(),
        let("search", search_term(collect), body))))))
    assert not t0erm_fvset(term), "the queens term must be closed"
    return term


########################################################################
# Driver: run the term, decode/print/check the resulting values
########################################################################

def decode_list(value):
    """Decode nested pairs ended by T0Mint(0) into a Python list of terms."""
    items = []
    while isinstance(value, T0Mpair):
        items.append(value.arg1)
        value = value.arg2
    assert value == T0Mint(0), f"malformed list ending: {value}"
    return items


def decode_board(value):
    return [c.arg1 for c in decode_list(value)]


def run_count(n):
    """Number of solutions for n queens, computed by the interpreter."""
    result = t0erm_cbv_evaluate0(T0Mapp(queens_term(False), T0Mint(n)))
    assert isinstance(result, T0Mint), result
    return result.arg1


def run_all(n):
    """(count, boards) for n queens; boards in the order they were found."""
    result = t0erm_cbv_evaluate0(T0Mapp(queens_term(True), T0Mint(n)))
    count = result.arg1.arg1
    boards = [decode_board(b) for b in decode_list(result.arg2)]
    boards.reverse()  # the accumulator is newest-first
    return count, boards


def is_valid_board(board, n=None):
    """n queens, one per row (by construction), no shared column or diagonal."""
    n = len(board) if n is None else n
    if len(board) != n:
        return False
    for r1 in range(n):
        if not 0 <= board[r1] < n:
            return False
        for r2 in range(r1 + 1, n):
            if board[r1] == board[r2] or abs(board[r1] - board[r2]) == r2 - r1:
                return False
    return True


def format_board(board):
    """The text printed by ATS's print_board."""
    n = len(board)
    return "".join(". " * c + "Q " + ". " * (n - c - 1) + "\n" for c in board) + "\n"


def main():
    n = 8
    if "--all" in sys.argv[1:]:
        count, boards = run_all(n)
        for k, bd in enumerate(boards, 1):
            print(f"Solution #{k}:\n")
            print(format_board(bd), end="")
    else:
        count = run_count(n)
    print(f"The total number of solutions is: {count}")
    assert count == 92


if __name__ == "__main__":
    main()
