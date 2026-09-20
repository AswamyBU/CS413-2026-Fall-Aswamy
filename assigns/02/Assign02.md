# Assignment #2
GitHub Repository and AI-Assisted Code Translation

## Due time: 11:59PM, Thursday, the 17th of September, 2026

## Attention

Everything you submit should stay in the MySolution directory
(that is, assigns/02/MySolution), which is already created for you.

## Objective

The purpose of this assignment is to gain practical experience with
abstract syntax trees (ASTs), which are used everywhere in compiler
construction, and with translating an existing ATS2 program into a
lambda-term represented by an AST.

As always, this assignment emphasizes that AI-generated code should be
treated as a draft that must be reviewed, tested, and corrected by the
programmer.

## Tasks

In the file lambda0.py, there is a substitution-based implementation
of an interpreter for a functional programming language (LAMBDA0) that
extends Church's lambda-calculus with some basic constructs. In particular,
recursion (T0Mfix) is supported.

Your task is to extend this implementation with pairs and projections.
The following AST constructors have already been added to `lambda0.py`,
but the implemented functions do not yet handle them:

| Constructor | Meaning |
| --- | --- |
| `T0Mpair(t1, t2)` | Construct a pair whose components are `t1` and `t2`. |
| `T0Mpfst(t1)` | Select the first component of the pair produced by `t1`. |
| `T0Mpsnd(t1)` | Select the second component of the pair produced by `t1`. |

### 1. Extend the AST operations

Copy `lambda0.py` into `MySolution/lambda0.py`. In your copy, add cases
for all three new constructors to each of these functions:

- `t0erm_size`: Count each pair or projection constructor as one node,
  in addition to the sizes of its subterms.
- `t0erm_fvset`: Collect free variables from both components of a pair,
  or from the operand of a projection. These constructors bind no variables.
- `t0erm_subst0`: Substitute recursively in both components of a pair,
  or in the operand of a projection, preserving the constructor. Keep
  the existing assumption that the replacement term is closed and preserve
  the binding behavior of `T0Mlam` and `T0Mfix`.

These operations must also work when pairs and projections occur inside
other constructs, or contain nested pairs and projections.

### 2. Extend call-by-value evaluation

Add cases to `t0erm_cbv_evaluate0` with the following behavior:

- For `T0Mpair(t1, t2)`, evaluate `t1` first and then `t2`, and return a
  `T0Mpair` containing the resulting values. A pair is a value only when
  both of its components are values.
- For `T0Mpfst(t1)`, evaluate `t1`. If the result is a pair value, return
  its first component; otherwise, raise `TypeError`.
- For `T0Mpsnd(t1)`, evaluate `t1`. If the result is a pair value, return
  its second component; otherwise, raise `TypeError`.

Pairs may contain values of different kinds, including other pairs and
functions. Preserve the existing behavior of all other constructs.

Both components of a pair must be evaluated even when a surrounding
projection selects only one of them. For example,
`T0Mpfst(T0Mpair(T0Mint(1), T0Mop2("/", T0Mint(1), T0Mint(0))))`
must raise `ZeroDivisionError`, rather than return `T0Mint(1)`.

### 3. Test your implementation

Create `MySolution/TEST/test02_lambda0.py` with automated tests for all
four extended functions. Include tests covering:

- Sizes and free-variable sets of pairs, projections, and nested terms.
- Substitution into both pair components and projection operands,
  including examples under lambda or recursive-function binders.
- Pair construction with components that require evaluation, and both
  projections of the resulting pair.
- Nested pairs and pairs containing different kinds of values.
- Functions that accept or return pairs, exercising substitution during
  application.
- A projection applied to a non-pair value, which must raise `TypeError`.
- Left-to-right evaluation of pair components and evaluation of the
  component that a projection does not select.

For example, the following results should hold:

```python
t0erm_size(T0Mpair(T0Mint(1), T0Mint(2))) == 3

t0erm_fvset(T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("y")))) == frozenset({"x", "y"})

t0erm_cbv_evaluate0(
    T0Mpsnd(T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3))))
) == T0Mint(5)
```

Turn these examples into assertions and add your own tests. Run the
existing tests against your extended implementation as well. Ensure that
all tests import `MySolution/lambda0.py`, rather than the starter file in
the assignment directory.

### 4. Translate an ATS2 eight-queens solution into a lambda-term

Take a previous solution to the eight-queens problem written in ATS2 and
translate it into a LAMBDA0 term of type `t0erm`. Identify the ATS2 source
you are translating and include a copy in `MySolution/`.

Create `MySolution/queens_lambda0.py` to construct the translated term and
run it with your extended `t0erm_cbv_evaluate0`. The search algorithm and
queen-conflict checks must be expressed in the lambda-term and executed
by the interpreter. Python helper functions may construct ASTs and display
or check the resulting values, but must not perform the search in place
of the translated program.

Use `T0Mlam`, `T0Mapp`, and `T0Mfix` for functions, application, and
recursion. Choose and document representations for boards and any lists
or other data structures used by the ATS2 program; pairs and projections
can help implement these representations. Construct a closed term so
that it is compatible with the interpreter's substitution assumptions.

If your translation needs primitive operations that the starter
interpreter does not yet support, such as integer comparisons, add the
necessary cases to your copy of the interpreter. Document these additions
and test them. Comparisons used as conditions should produce `T0Mbtf`
values.

Add `MySolution/TEST/test03_queens.py` to test the translation. Compare its
results with those of the original ATS2 program, preserving whether that
program finds one solution, counts solutions, or enumerates them. Check
that any returned board places eight queens with no shared row, column,
or diagonal. Test the conflict-checking logic and smaller board sizes
where your implementation supports them.

In your `README.md`, explain how the main ATS2 functions and data
structures map to LAMBDA0 terms, give commands to run the translation and
its tests, and report the comparison with the original program. Discuss
any changes needed for call-by-value evaluation and any limitations you
encountered.

## Submission

Keep all submitted files under `MySolution/`:

- `lambda0.py`: Your extended implementation.
- `TEST/test02_lambda0.py`: Your tests for pairs and projections.
- `queens_lambda0.py`: Your eight-queens lambda-term and evaluation driver.
- `TEST/test03_queens.py`: Your tests for the translated solution.
- The original ATS2 eight-queens source used for the translation.
- `README.md`: Briefly explain your changes, give the commands to run
  your tests, and summarize the results. Describe how you reviewed and
  verified any AI-generated code you used.

Use Python 3.12 or later, as required by the starter code's type-alias
syntax. Do not modify the starter file outside `MySolution/` for your
submission.
