# Assignment 5: Pretty Printing and Capture-Avoiding Substitution with Visitors

Python 3.12 or later is required, because the supplied `lambda1_vp.py` uses
`type` aliases. I developed and tested with Python 3.14.0. The supplied files in
`assigns/05` are unchanged; everything new is in this directory.

| File | Contents |
| --- | --- |
| `lambda1_visitors.py` | `PrettyPrintVisitor`, `d0exp_pretty`, `AllNamesVisitor`, `d0exp_names`, `FreshNames`, `SubstitutionVisitor`, `d0exp_substitute` |
| `TEST/test_unittest_visitors.py` | The `unittest` suite (`unittest.TestCase` classes) |
| `TEST/test_pytest_visitors.py` | The `pytest` suite (plain test functions and `assert`) |

`lambda1_visitors.py` adds `assigns/05` to `sys.path` and imports the expression
classes, `D0ExpVisitor`, and `d0exp_fvset` from `lambda1_vp.py`.

## Setup

```sh
python -m pip install pytest        # only needed for the pytest suite
```

(`python3` may be the interpreter name on macOS/Linux.)

## Running the tests

Run both commands from `assigns/05`:

```sh
# unittest suite (standard library only)
python -m unittest discover -s MySolution/TEST -p "test_unittest_*.py" -v

# pytest suite
python -m pytest MySolution/TEST/test_pytest_visitors.py -v
```

Each suite runs on its own, and they do not import each other.

## Examples

```python
import sys; sys.path.insert(0, "MySolution")
from lambda1_visitors import d0exp_pretty, d0exp_substitute
from lambda1_vp import *

e = D0Eapp(D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(4))
d0exp_pretty(e)                       # '((lam x. (x + 1)) 4)'

e = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
d0exp_pretty(d0exp_substitute(e, "x", D0Evar("y")))
                                      # '(lam y_1. (y + y_1))'

e = D0Efix("f", "n", D0Eop2("+", D0Evar("x"), D0Eapp(D0Evar("f"), D0Evar("n"))))
d0exp_pretty(d0exp_substitute(e, "x", D0Eapp(D0Evar("f"), D0Evar("n"))))
                                      # '(fix f_1(n_1). ((f n) + (f_1 n_1)))'
```

## Fresh-name policy

Each call to `d0exp_substitute(e, x, r)` builds one `FreshNames` supply. It
starts with a *used* set made of every name in `e` and in `r` (free variables,
bound occurrences, and binder names, collected by `AllNamesVisitor`) plus the
target `x`. To rename a binder `y`, it tries `y_1`, `y_2`, `y_3`, ... and picks the
first one that is not used yet. That name is then added to the used set. This
means a generated name never matches an existing name, the target, or an
earlier generated name in the same call, and the same input always gives the
same output.

A binder is renamed only if (a) some pending substitution can actually fire in
its scope, meaning its variable is free in the body and not shadowed by this
binder, and (b) the binder's name occurs free in that substitution's
replacement. When `fix f(f)` has to be renamed, both positions get the same
fresh name, so the parameter still shadows the function name.

## Design Explanation (Reflection)

### Result types

Each operation is its own visitor with its own result type. The pretty printer
returns a string, the substitution visitor returns a new expression tree, and
the name collector returns a set of names, like the supplied
`FreeVariableVisitor`. The generic `R` on `D0ExpVisitor` makes this work, since
`accept` just hands back whatever the visitor produces. I never check what kind
of node I'm looking at, because each `visit_*` method already knows.

### Carrying context through substitution

Printing needs no context, but substitution has to know what to replace and
how to make new names. My `SubstitutionVisitor` keeps a map called `sigma` from
names to their replacements, plus a fresh-name generator shared across the
whole call. A call to `e[x := r]` starts with `sigma = {x: r}`.

When the visitor reaches a binder, it doesn't change itself. It builds a new
visitor for the body instead, the same way `EvaluateVisitor` builds a new one
for each new environment. So whatever changes inside a body stays there, and
nothing leaks into neighbouring subtrees or into a `let` initializer, which is
visited with the outer visitor. The fresh-name generator is the only shared
state, and that's on purpose, since it keeps generated names from repeating.

### Renaming and scope

At a binder, I first remove the binder's own name from `sigma`, since inside
the body that name refers to the binder and not to anything outside. Then I
keep only the entries whose names are actually free in the body. If nothing is
left, there is nothing to substitute here, so nothing gets renamed. Otherwise,
any binder whose name shows up free in a remaining replacement is renamed to a
fresh name, and an entry like `y -> y_1` is added to the body's `sigma`.

So renaming is really just one more substitution, and it follows the same
scoping rules as the main one. If an inner `lam y` rebinds `y`, the `y -> y_1`
entry is dropped at that point, and the inner `y` is left alone. A simple
find-and-replace on strings would get this wrong. For `fix`, I go through the
binders from the outside in (`f` first, then `x`). If both have the same name,
they both get the same new name, which keeps the evaluator's rule that the
parameter shadows the function name.

### Adding operations vs. adding constructors

With visitors, adding a new operation is easy. You write one new class with a
method per constructor, and nothing else changes. I did exactly that three
times in this assignment.

Adding a new kind of expression is the opposite. You need a new class with an
`accept` method, a new abstract `visit_*` method on `D0ExpVisitor`, and an
implementation of it in every visitor that already exists (free variables,
evaluation, printing, name collection, and substitution). Since the method is
abstract, any visitor you forget to update can't even be created. That's the
classic trade-off of the Visitor pattern, sometimes called the expression
problem: new operations are cheap, and new kinds of data are expensive.

## Known limitations

- The traversals are recursive, so very deep expressions (around 1000 levels)
  can hit Python's recursion limit.
- `_enter` recomputes the free variables of the body at each binder, so
  substitution is quadratic in the worst case. That is fine at the size of
  these tests.
- The replacement expression is shared, not copied, at each insertion point.
  This is allowed, but if a caller later mutated the result in place, the
  replacement would change too. Nothing here mutates ASTs.
- Names are not validated. If an input already uses names like `y_1`, the
  generated names skip past them, as the tests show.
