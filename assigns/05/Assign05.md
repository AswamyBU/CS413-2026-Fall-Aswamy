# Assignment #5
Pretty Printing and Capture-Avoiding Substitution with Visitors

## Due date

Tuesday, October 13, 2026.

## Attention

Keep everything you submit in `assigns/05/MySolution/`.

## Objective

Use the Visitor pattern to add two operations to the supplied LAMBDA abstract
syntax tree (AST): pretty printing and capture-avoiding substitution. Practice
recursive traversal, operations with different result types, and lexical scope.

## Starting point

Use **Python 3.12 or later** and the supplied visitor-based implementation,
[lambda1_vp.py](./lambda1_vp.py). All submitted code and tests must use Python.

The [Java](./JAVA/Lambda1_vp.java) and
[JavaScript](./NODE/lambda1_vp.js) implementations in this directory are provided
only to demonstrate that the Visitor pattern can also be implemented in Java
and JavaScript. They are not alternative languages for this assignment.

Study `D0ExpVisitor`, `FreeVariableVisitor`, and `EvaluateVisitor`. Your visitors
must work with the existing expression classes and dispatch through `accept`.
Do not change the supplied interpreter files or expression classes. Put new
visitors, helpers, and tests in `MySolution/`, importing
the supplied implementation. You may reuse `d0exp_fvset`.

Implement every expression form, including `fix`, `let`, pairs, and projections.
Do not replace visitor dispatch with a central chain of type or tag tests.
Helper traversals over expressions must also use visitors. Neither operation
should evaluate the input expression. A parser or web interface is not required.

## Task 1: Pretty printing

Implement `PrettyPrintVisitor`, whose result is a string, and expose a function
equivalent to:

```text
d0exp_pretty(expression) -> string
```

Use the following exact, single-line format. In this table, `P(e)` means the
pretty-printed form of `e`; names and operators are inserted literally.

| Expression | Output format |
| --- | --- |
| `D0Eint(n)` | Decimal integer, without a language-specific suffix |
| `D0Ebtf(b)` | `true` or `false` |
| `D0Evar(x)` | `x` |
| `D0Eop1(op, e)` | `(op P(e))` |
| `D0Eop2(op, e1, e2)` | `(P(e1) op P(e2))` |
| `D0Elam(x, body)` | `(lam x. P(body))` |
| `D0Efix(f, x, body)` | `(fix f(x). P(body))` |
| `D0Eapp(e1, e2)` | `(P(e1) P(e2))` |
| `D0Eif0(c, t, f)` | `(if P(c) then P(t) else P(f))` |
| `D0Elet(x, init, body)` | `(let x = P(init) in P(body))` |
| `D0Epair(e1, e2)` | `(pair P(e1) P(e2))` |
| `D0Epfst(e)` | `(fst P(e))` |
| `D0Epsnd(e)` | `(snd P(e))` |

Use the spaces shown above, with no leading/trailing whitespace or final
newline. For this assignment, variable names are nonempty identifiers matching
`[A-Za-z_][A-Za-z0-9_]*`; input validation is not required.

For example, the following Python constructor expression:

```python
D0Eapp(D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(4))
```

must print as:

```text
((lam x. (x + 1)) 4)
```

Printing `D0Eop2("/", D0Eint(1), D0Eint(0))` must produce `(1 / 0)`
without raising a division-by-zero error.

## Task 2: Capture-avoiding substitution

Implement `SubstitutionVisitor`, whose result is an expression, and expose a
function equivalent to:

```text
d0exp_substitute(expression, variable, replacement) -> expression
```

Write `e[x := r]` for replacing the **free occurrences** of variable `x` in
expression `e` with expression `r`. The replacement may itself contain free
variables. These must remain free when inserted: an enclosing binder must not
accidentally capture them.

This is a single substitution. Insert `r` as an expression; do not recursively
substitute inside the inserted replacement. Do not evaluate or simplify the
result, and do not mutate either input AST. Reusing unchanged subtrees is allowed.

### Binding rules

- A lambda binds its parameter in its body.
- A `fix` binds both its function name and its parameter in its body.
- A nonrecursive `let` binds its name only in its body, **not** in its initializer.
- Other expression forms introduce no bindings.

For literals, return an equivalent literal. For a variable occurrence, return
the replacement exactly when its name matches the substitution target. For
forms without binders, recursively transform each child and preserve the
constructor and operator.

At a binder, stop substitution in any region where the target is bound. Before
inserting a replacement under a conflicting binder, rename that binder and
the occurrences it binds to a fresh name. This operation is called
**alpha-renaming**. Renaming must respect nested shadowing; global string
replacement is not correct.

For `let`, always substitute in the initializer, even when the let-bound name
equals the target. Alpha-renaming the let-bound name changes its bound
occurrences in the body, not occurrences in the initializer.

Handle both binders of `fix`. If its function name and parameter are the same,
the parameter shadows the function name, matching the supplied evaluator.
Your renaming must preserve that behavior.

### Fresh names

Use a deterministic fresh-name policy, and document it. Generated names must
avoid **all** variable and binder names in the original expression and the
replacement, the substitution target, and names already generated during that
call. A visitor collecting all names, followed by a counter-based generator,
is one possible approach. Free-variable names alone are insufficient for this
freshness requirement.

Different choices of fresh names are acceptable. Results are judged up to
alpha-equivalence: changing bound names consistently does not change meaning.
Avoid unnecessary renaming when no substitution can occur in a binder's scope.

### Examples

The expressions below use the pretty-printing notation from Task 1. Fresh
names such as `y_1` and `f_1` are illustrative.

| Expression | Substitution | One acceptable result |
| --- | --- | --- |
| `(x + z)` | `x := 3` | `(3 + z)` |
| `(lam x. (x + y))` | `x := 3` | `(lam x. (x + y))` |
| `(lam y. (x + y))` | `x := y` | `(lam y_1. (y + y_1))` |
| `(let x = x in (x + y))` | `x := 3` | `(let x = 3 in (x + y))` |
| `(let y = x in (x + y))` | `x := y` | `(let y_1 = y in (y + y_1))` |
| `(fix f(n). (x + (f n)))` | `x := f` | `(fix f_1(n). (f + (f_1 n)))` |
| `x` | `x := (x + 1)` | `(x + 1)` |

For example, substituting `x := y` into `(lam y. (x + y))` must **not**
produce `(lam y. (y + y))`: that result captures the formerly free `y`.

## Testing

Provide **two separate sets of automated tests** with explicit expected results:

- One suite using Python's standard-library `unittest` framework, with test
  cases derived from `unittest.TestCase`.
- One suite using `pytest`, with pytest-style test functions and plain `assert`
  statements. Running the `unittest` suite through pytest does not count as
  the second suite.

Both suites must cover the requirements below. They may share example inputs
and expected results, but each must run independently. Cover:

1. Exact pretty-printing output for every expression constructor, nested
   expressions, negative and large integers, and both boolean values.
2. Substitution through every expression constructor; matching and nonmatching
   variables; and replacement expressions containing the target itself.
3. Shadowing by lambdas, both `fix` binders, and `let`; include a `fix` whose
   function name equals its parameter.
4. Capture avoidance for lambda, `let`, and each `fix` binder, including a
   replacement that conflicts with both distinct `fix` binders.
5. Nested shadowing during alpha-renaming and fresh-name collisions with
   existing bound names and names generated earlier in the same call.
6. The distinction between a let initializer and its body.
7. Preservation of both input ASTs, deterministic results across repeated
   calls, and absence of evaluation during printing and substitution.

Also check the following free-variable property on several examples. If
`x` occurs free in `e`, then:

```text
FV(e[x := r]) = (FV(e) - {x}) union FV(r)
```

If `x` does not occur free in `e`, the result must be alpha-equivalent to `e`
and have the same free variables. The free-variable property alone does not
prove correct substitution; include structural or exact-output checks too.
Tests may use your documented fresh-name policy for exact expected outputs;
an alpha-equivalence checker is not required.

## Submission

Submit the following under `MySolution/`:

- Source for both visitors, entry points, and any helper visitors.
- Both the `unittest` and `pytest` suites, with a separate documented command
  to run each suite.
- `README.md` with the Python version, setup commands (including installation
  of pytest), examples,
  fresh-name policy, and any known limitations.
- A short design explanation (approximately 300–500 words) in `README.md`:
  explain visitor result types, how substitution carries context, how renaming
  respects scope, and why adding an operation differs from adding a new
  expression constructor in this design.
- `AI-TRANSCRIPT.md`: AI tools used, important prompts and suggestions, and how
  you reviewed and tested their output. If you did not use AI, state that here.

Do not submit installed dependencies, compiled classes, or caches. Verify your
documented commands for both test suites from the assignment directory.

## Evaluation

| Criterion | Weight |
| --- | --- |
| Pretty-printing correctness and complete constructor coverage | 20% |
| Capture-avoiding substitution, binding rules, and fresh names | 45% |
| Appropriate visitor design and preservation of input ASTs | 15% |
| Both test suites, including scope and capture edge cases | 15% |
| Clear documentation and design explanation | 5% |

Correct output alone does not fulfill the design requirement: both operations
must be implemented through the supplied Visitor interface.
