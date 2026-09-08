"""
The Eight Queens puzzle.

Python 3 translation of the ATS program in ``queens.dats``.  The goal is to
preserve the behavior (and, as far as Python allows, the structure) of the
original as closely as possible.

Representation
--------------
The board is an 8-tuple of ints, exactly like the ATS ``int8`` type.
``bd[k]`` is the column of the queen placed on row ``k`` (``-1`` means "unset").
Tuples are immutable, matching the value semantics of the ATS tuple: every
"update" produces a brand new board.

Deviation from the original
---------------------------
ATS guarantees tail-call optimization, so the original ``search`` function is
written as a set of mutually tail-recursive calls that never grow the stack.
Python has no TCO, and the 8-queens search performs many thousands of these
steps, which would overflow Python's call stack.  Because every self-call in
the original ``search`` is in tail position, rewriting it as a ``while`` loop
that reassigns the parameters is a behavior-preserving transformation, and
that is what is done below.  The helper functions (``print_dots``,
``safety_test2``) recurse to a depth of at most ``N`` (8), so they are left
recursive to stay faithful to the source.
"""

N = 8


def print_dots(i):
    # if i > 0 then (print ". "; print_dots (i-1)) else ()
    if i > 0:
        print(". ", end="")
        print_dots(i - 1)
    else:
        pass


def print_row(i):
    # print_dots (i); print "Q "; print_dots (N-i-1); print "\n";
    print_dots(i)
    print("Q ", end="")
    print_dots(N - i - 1)
    print("\n", end="")


def print_board(bd):
    print_row(bd[0]); print_row(bd[1]); print_row(bd[2]); print_row(bd[3])
    print_row(bd[4]); print_row(bd[5]); print_row(bd[6]); print_row(bd[7])
    print("\n", end="")  # print_newline ()


def board_get(bd, i):
    if i == 0:
        return bd[0]
    elif i == 1:
        return bd[1]
    elif i == 2:
        return bd[2]
    elif i == 3:
        return bd[3]
    elif i == 4:
        return bd[4]
    elif i == 5:
        return bd[5]
    elif i == 6:
        return bd[6]
    elif i == 7:
        return bd[7]
    else:
        return -1


def board_set(bd, i, j):
    x0, x1, x2, x3, x4, x5, x6, x7 = bd
    if i == 0:
        x0 = j
    elif i == 1:
        x1 = j
    elif i == 2:
        x2 = j
    elif i == 3:
        x3 = j
    elif i == 4:
        x4 = j
    elif i == 5:
        x5 = j
    elif i == 6:
        x6 = j
    elif i == 7:
        x7 = j
    else:
        return bd
    return (x0, x1, x2, x3, x4, x5, x6, x7)


def safety_test1(i0, j0, i1, j1):
    # abs: the absolute value function
    # j0 != j1 andalso abs (i0 - i1) != abs (j0 - j1)
    return j0 != j1 and abs(i0 - i1) != abs(j0 - j1)


def safety_test2(i0, j0, bd, i):
    if i >= 0:
        if safety_test1(i0, j0, i, board_get(bd, i)):
            return safety_test2(i0, j0, bd, i - 1)
        else:
            return False
    else:
        return True


def search(bd, i, j, nsol):
    # Iterative rendering of the original's tail-recursive control flow.
    while True:
        if j < N:
            test = safety_test2(i, j, bd, i - 1)
            if test:
                bd1 = board_set(bd, i, j)
                if i + 1 == N:
                    print("Solution #", nsol + 1, ":\n\n", sep="", end="")
                    print_board(bd1)
                    # search (bd, i, j+1, nsol+1)
                    j = j + 1
                    nsol = nsol + 1
                    continue
                else:
                    # search (bd1, i+1, 0, nsol)  -- positioning next piece
                    bd = bd1
                    i = i + 1
                    j = 0
                    continue
            else:
                # search (bd, i, j+1, nsol)
                j = j + 1
                continue
        else:
            if i > 0:
                # search (bd, i-1, board_get (bd, i-1) + 1, nsol)
                j = board_get(bd, i - 1) + 1
                i = i - 1
                continue
            else:
                return nsol


def main():
  bd0 = (-1, -1, -1, -1, -1, -1, -1, -1)
  nsol = search(bd0, 0, 0, 0)
  print("The total number of solutions is: ", nsol, "\n", sep="", end="")


  #TEST CASES
  assert nsol == 92, "normal: 8-queens has 92 solutions"
  print("normal case (full solver -> 92 solutions): PASS")

  assert board_get((0,) * N, N) == -1, "edge: index N (just past the end) should return -1"
  assert board_get((0,) * N, -1) == -1, "edge: negative index should return -1"
  print("edge cases (board_get out of range --> -1): PASS")

  assert safety_test1(0, 0, 2, 2) is False, "normal: same diagonal -> not safe"
  assert safety_test1(0, 0, 2, 0) is False, "normal: same column -> not safe"
  assert safety_test1(0, 0, 2, 3) is True,  "normal: different col and diagonal -> safe"
  print("safety_test1 (column/diagonal attack rule): PASS")



if __name__ == "__main__":
    main()