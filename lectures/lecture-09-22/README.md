# Closure-based LAMBDA interpreter

`lambda1.py` implements a closure-based, call-by-value interpreter. It requires
Python 3.12 or later. Programs are constructed directly as Python AST objects;
there is no source-text parser.

Run the tests from this directory:

```sh
python3 -B -m unittest discover -s TEST -v
```

To also check that runtime type checks remain active under `-O` and `-OO`:

```sh
make -C TEST test-all
```

## Expressions and values

`d0exp_evaluate(dexp, denv=ENVnil())` evaluates an expression in an optional
explicit environment. Free variables are resolved through that environment.

| Expression | Meaning / resulting value |
| --- | --- |
| `D0Eint(n)` | Integer literal; produces `D0Vint(n)`. |
| `D0Ebtf(b)` | Boolean literal; produces `D0Vbtf(b)`. |
| `D0Evar(name)` | Look up a variable in the environment. |
| `D0Elam(parameter, body)` | Produces `D0Vlam(env, code)`. |
| `D0Efix(name, parameter, body)` | Produces recursive closure `D0Vfix(env, code)`. |
| `D0Eapp(function, argument)` | Apply a closure to an evaluated argument. |
| `D0Elet(name, value, body)` | Evaluate value, then evaluate body with name bound to that value. |
| `D0Eop1(name, operand)` | Unary integer operation: `+1` or `-1`. |
| `D0Eop2(name, left, right)` | Integer arithmetic or comparison. |
| `D0Eif0(condition, then_branch, else_branch)` | Boolean conditional, despite the `if0` name. |
| `D0Epair(first, second)` | Produces `D0Vpair(first_value, second_value)`. |
| `D0Epfst(pair)` / `D0Epsnd(pair)` | Return the first / second component of an evaluated pair. |

Binary arithmetic supports `+`, `-`, `*`, and `/`. Division uses Python integer
floor division (`//`), so dividing `-7` by `3` produces `D0Vint(-3)`.
Comparisons `<`, `>`, `<=`, `>=`, `==`, and `!=` accept integer values and produce
`D0Vbtf` values. Strings and modulo are not supported.

For example:

```python
from lambda1 import D0Eapp, D0Eint, D0Elam, D0Eop1, D0Evar, D0Vint, d0exp_evaluate

increment = D0Elam("x", D0Eop1("+1", D0Evar("x")))
assert d0exp_evaluate(D0Eapp(increment, D0Eint(41))) == D0Vint(42)
```

## Environments and evaluation

`ENVnil()` is the empty environment. `ENVcns(name, value, outer)` adds a binding;
`d0env_search(env, name)` returns the nearest matching binding. Environment links
are immutable, although the ASTs and values they reference are not frozen.

A lambda captures its definition environment without evaluating its body.
Application evaluates the function and argument, then evaluates the body in the
captured environment extended with the parameter binding. A recursive closure
additionally binds its own name to itself at application time. The parameter
shadows the recursive name when both names coincide. This implements lexical
scope without substitution or AST copying during evaluation.

Evaluation proceeds left to right, including both binary operands and both pair
components. Arguments are evaluated even when unused. A projection evaluates
its operand fully, including the pair component it discards. Pairs may contain
values of different kinds, nested pairs, and closures.

A conditional requires a `D0Vbtf` condition and evaluates only the selected
branch: the second argument for true and the third for false.

A let evaluates its initializer in the current environment, even if the binding
is unused. Its binding shadows any outer binding only within the body; the
initializer can still refer to the outer binding. Let bindings are nonrecursive.

## Errors

Unbound variables return `D0V000()`, an error sentinel; they do not raise
`NameError`. The sentinel can be returned directly or stored in a pair.
Invalid operand kinds, unsupported operators or expressions, application of a
nonclosure, and projection of a nonpair raise `TypeError`. Division by zero
raises `ZeroDivisionError`.

Application evaluates its argument before checking that the function value is
a closure. Binary operations evaluate both operands before checking the operator
and operand kinds. An error during that evaluation therefore takes precedence
over these checks.

ASTs and environments are assumed to have correctly typed fields; dataclass
annotations do not validate constructor arguments. Evaluation uses Python
recursion and does not guarantee termination or tail-call optimization.
