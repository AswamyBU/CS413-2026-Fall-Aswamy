# Assignment 2: pairs/projections in LAMBDA0 and eight queens as a lambda-term

Needs Python 3.12+ since the starter uses `type` aliases. Everything lives in
this directory and the starter file in `assigns/02` is untouched.

| File | Contents |
| --- | --- |
| `lambda0.py` | The extended interpreter (copy of the starter plus my changes). |
| `TEST/test01_lambda0.py` | The starter's tests, unchanged, run against my copy. |
| `TEST/test02_lambda0.py` | Tests for pairs and projections. |
| `queens.dats` | The ATS2 source that was translated (copied from `assigns/01/MySolution/queens.dats`, Hongwei Xi's eight-queens example). |
| `queens_lambda0.py` | Builds the eight-queens `t0erm` and runs it with `t0erm_cbv_evaluate0`. |
| `TEST/test03_queens.py` | Tests for the translation. |

## Commands

```
# from assigns/02/MySolution
python3 queens_lambda0.py           # counts the solutions for N = 8 (about 20 s)
python3 queens_lambda0.py --all     # also prints every solution (about 35 s)

cd TEST
python3 -m unittest discover -s . -p 'test*.py' -v    # everything (about 105 s)
python3 test02_lambda0.py                              # pairs/projections only (instant)
python3 test03_queens.py                               # queens only (about 100 s)
# or: make          (or: make TEST=test02_lambda0.py)
```

All the tests import `MySolution/lambda0.py` (the test files stick
`MySolution/` at the front of `sys.path`).

## Part 1-3: pairs and projections

I added `T0Mpair`, `T0Mpfst`, `T0Mpsnd` to the interpreter. `t0erm_size` just
counts one node plus whatever the subterms cost. `t0erm_fvset` takes the union
of the components' free variables (or the operand's, for a projection) since
none of these bind anything. `t0erm_subst0` recurses into both components (or
the operand) and keeps the constructor; `T0Mlam` and `T0Mfix` binding is
unchanged. For evaluation, a pair evaluates its first component and then its
second and returns a `T0Mpair` of the two values; `T0Mpfst`/`T0Mpsnd` evaluate
their operand, return the matching component of a pair, and raise `TypeError`
if the operand isn't one. Both components always get evaluated, so
`fst (1, 1/0)` raises `ZeroDivisionError` rather than short-circuiting.

`test02_lambda0.py` covers sizes and free variables (nested terms, binders),
substitution into both components and into projection operands (also under
`T0Mlam`/`T0Mfix`), evaluation, nested and mixed pairs (pairs holding
functions and other pairs), functions taking and returning pairs, recursion
over pairs, the `TypeError` on projecting a non-pair, and the left-to-right
evaluation order including the unselected component. The spec's own examples
show up as `TestSize.test_pair`, `TestFreeVariables.test_nested`,
`TestEvaluatePairs.test_spec_example`, and
`TestEvaluationOrder.test_unselected_component_is_evaluated`.

## Part 4: eight queens

### Mapping from ATS2 to LAMBDA0

| ATS2 | LAMBDA0 term (in `queens_lambda0.py`) |
| --- | --- |
| `int8` board, an 8-tuple of columns | Right-nested pairs `(x0, (x1, (... (x_{n-1}, 0))))` ended by `T0Mint(0)`. `x_k` is the column of row `k`. Unset rows hold 0, like the ATS initial board `(0,...,0)`. |
| `#define N 8` | The term is `lambda n. ...`, so `N` is a parameter (smaller boards can be tested). |
| `board_get (bd, i)` (8-way `if`) | `bget`: `fix bget bd. lambda i. if i == 0 then fst bd else bget (snd bd) (i-1)` |
| `board_set (bd, i, j)` | `bset`: rebuilds the list, replacing element `i` (functional, like the ATS tuple). |
| `abs` | `abs_term`: `lambda x. if x < 0 then -x else x` |
| `safety_test1 (i0, j0, i, j)` | `j0 != j andalso abs(i0-i) != abs(j0-j)` where `andalso` is `if a then b else false`. |
| `safety_test2 (i0, j0, bd, i)` | `fix st2 ...`, recursing from row `i` down to 0 and calling `st1` and `bget`. |
| `search (bd, i, j, nsol)` | `fix search bd. lambda i. lambda j. lambda acc. ...`, basically a direct rendering of the ATS control flow: try column `j`, place the next queen, record a solution and continue at `j+1`, or backtrack to row `i-1` at column `board_get(bd,i-1)+1`. |
| `main0`: `search ((0,..,0), 0, 0, 0)` | `search (mk n) 0 0 0` where `mk k` builds a board of `k` zeros. |
| `let x = e in b` | `(lambda x. b) e` |
| multi-argument functions | Curried: `f a b c` is `T0Mapp(T0Mapp(T0Mapp(f,a),b),c)`; recursive functions are a `T0Mfix` whose body is a chain of `T0Mlam`. |

The whole program is one closed term (`queens_term`, and I assert it's closed
with `t0erm_fvset`). Helper functions are `let`-bound to closed function
values so substitution's "replacement term is closed" assumption actually
holds. The Python in `queens_lambda0.py` only builds ASTs and decodes/prints
results, there's no search logic hiding in it.

**Counting vs. printing.** The ATS program counts solutions (`nsol`, checked
against 92) and prints each board as it's found. A term can't print though, so
there end up being two builds of the same `search`: `queens_term(False)` keeps
`acc` as just the integer count, exactly like `nsol`, while
`queens_term(True)` keeps `acc = (count, list of boards)`, consing each
solution on as it's found. Python then decodes that list (reversing it, since
the newest is first) and prints the boards in the ATS `print_board` format.

### Changes to the interpreter (all in my `lambda0.py`)

No new primitive operations were needed, the starter already had `<`, `>`,
`<=`, `>=`, `==`, `!=` (producing `T0Mbtf`) and `+ - * / %`. I made three
changes though, and none of them change what a term evaluates to.

First, tail calls loop instead of recurse in `t0erm_cbv_evaluate0` (the body
of an application, and the chosen branch of an `if`). The ATS `search` is
tail-recursive and ATS guarantees tail-call optimization, so without this
change the Python stack would blow out after the tens of thousands of search
steps. Second, free-variable sets are memoized (by object identity, and
dropped once the term is garbage collected), and `t0erm_subst0` now returns a
subterm unchanged when the variable isn't free in it, since otherwise inlined
closed helper functions get re-copied on every single call. Third, `T0M000`
no longer derives from `ABC`. It had no abstract methods anyway, and the ABC
metaclass was making every `isinstance` check slow, profiling showed that was
eating most of the runtime.

The second and third changes together took `queens 8` from about 93 s down to
about 20 s. Tests for these are in `TestInterpreterAdditions` in
`test03_queens.py` (a 20000-deep tail loop, checking non-tail recursion still
works, substitution and cache correctness, and comparisons producing
`T0Mbtf`).

### Comparison with the original ATS program

I did not actually run the ATS program (no ATS compiler was used here). So the
comparison is against what the ATS source specifies, plus an independent
plain-Python reference implementation:

- The ATS program counts and prints solutions and asserts `nsol = 92`; the
  term returns 92 for `N = 8` (`test03_queens.py` also checks that the copied
  `queens.dats` still has that assertion in it).
- The term's solutions (from the collecting build) are exactly the 92 boards
  of a reference enumerator (`itertools.permutations` filtered by a plain
  Python validity check), in the same order the ATS search finds them
  (lexicographic). The first is `[0,4,7,5,2,6,1,3]` and the last
  `[7,3,0,2,5,1,6,4]`.
- Every returned board has eight queens with no shared row (guaranteed by
  construction, one per row), column, or diagonal, and all 92 are distinct.
- Printed boards use the same text format as `print_board`.
- Smaller boards, N = 1..7, give 1, 0, 0, 2, 10, 4, 40 solutions (these are
  known values), and the collecting build's solutions match the reference
  there too.
- `safety_test1` gets checked against the Python rule on all 256 inputs with
  values in 0..3, and `safety_test2`, `board_get`, `board_set`, `abs`, `mk`
  each have their own direct tests.

### Limitations

It's slow: a substitution-based interpreter rewrites terms on every call, so
N = 8 takes about 20 s and the full test suite runs about 105 s. There are a
few deviations from the ATS source too: `N` is a parameter here; boards are
pair-lists, so `board_get`/`board_set` past the end raise `TypeError` where
the ATS version would return 0 or leave the board unchanged (the search never
actually hits this case); and solutions get accumulated instead of printed,
as explained above. Also, since call-by-value evaluates all arguments before
the call, `andalso` and `if` are implemented with `T0Mif0` (which only
evaluates the chosen branch) instead of as ordinary functions. Deep non-tail
recursion is still bounded by Python's recursion limit, only tail calls are
unbounded.

## How the AI-generated code was reviewed and verified

The code in this directory was drafted with Claude Code and then checked as
follows. (Add your own review notes here before submitting.)

I read the assignment and the starter first, then wrote the pair/projection
cases to mirror the ones already there, and ran the starter tests (`test01`)
unchanged against the extended copy after every interpreter change. I wrote
`test02` from the spec's list and its three worked examples, including the
error case and the evaluation-order case, and cleaned up a couple of tests
the draft had made clumsy before running anything. The first complete queens
term did return 92, but it took 93 s, so I profiled it with `cProfile`, found
the `ABC` and substitution costs, and re-ran all the tests after each
optimization to make sure nothing broke. I didn't just trust the count
either: `test03` compares against known counts, an independent reference
enumerator (including the order), a board-validity checker, exhaustive checks
of the conflict test, and the ATS source itself. Finally I ran the `--all`
driver and looked over the printed boards by hand.
