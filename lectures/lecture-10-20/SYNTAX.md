# LAMBDA concrete syntax

The parser is in `lambda2.py` and requires Python 3.12 or later.

```python
from lambda2 import d0exp_parse, d0exp_evaluate, d0cls_parse, D0Elets, D0Evar

value = d0exp_evaluate(d0exp_parse('let x = 6 in x * 7 end'))
# D0Vint(42)
declarations = d0cls_parse('x = 6; answer = x * 7')
value = d0exp_evaluate(D0Elets(declarations, D0Evar('answer')))
# D0Vint(42)
```

`d0exp_parse` consumes one complete expression. `d0cls_parse` consumes a
sequence of declarations and returns `fnlist[d0cls]`. Invalid source raises
`LambdaSyntaxError`, a `SyntaxError` subclass with line and column information.
Parsing constructs syntax trees without evaluating them.

## Grammar

Here `{ ... }` means repetition, `[ ... ]` means optional, and quoted strings
are literal tokens.

```text
declarations   = { identifier "=" expression [";"] } ;
expression     = "lam" "(" identifier ")" "=>" expression
               | "fix" identifier "(" identifier ")" "=>" expression
               | "if" expression "then" expression "else" expression
               | "let" declarations "in" expression "end"
               | comparison ;
comparison     = additive [ comparison-op additive ] ;
comparison-op  = "<" | ">" | "<=" | ">=" | "==" | "!=" ;
additive       = multiplicative { ("+" | "-") multiplicative } ;
multiplicative = unary { ("*" | "/") unary } ;
unary          = ("+" | "-") unary | postfix ;
postfix        = atom { parenthesized | "." integer } ;
atom           = integer | "true" | "false" | identifier | parenthesized
               | "list_nil" "(" ")"
               | "list_cons" "(" expression "," expression ")"
               | ("list_nilq" | "list_head" | "list_tail") "(" expression ")"
               | "optn_nil" "(" ")"
               | ("optn_cons" | "optn_nilq" | "optn_get" | "print") "(" expression ")" ;
parenthesized  = "(" [ expression [ "," [ expression { "," expression } [","] ] ] ] ")" ;
```

Identifiers match `[A-Za-z_][A-Za-z_0-9]*`. Keywords are reserved and
case-sensitive. Integers are nonnegative decimal tokens; negative expressions
use unary minus. Whitespace, including newlines, is insignificant. `#` starts
a comment extending to the end of the line. Declaration semicolons are optional:
`let x = 1 y = x + 1 in y end` is valid. A declaration initializer ends when
its expression ends; a following identifier followed by `=` starts the next
declaration. Bare juxtaposition is not function application.

## Meaning and precedence

From strongest to weakest: calls and projections, unary signs, multiplication
and division, addition and subtraction, comparisons. Binary arithmetic is
left-associative; comparisons cannot be chained. Parentheses override precedence.
Lambda, fix, if, and let extend as far right as their enclosing syntax permits;
parenthesize them when used as arithmetic operands or as the function in a call.
Each `if` requires both `then` and `else`.

- `lam (x) => body` creates a function with one parameter.
- `fix f(x) => body` binds both `f` and `x` in the body for recursion.
- `let x = e1 y = e2 in body end` creates `D0Elets` with `D0Cval`
  declarations in an `fnlist`. Each binding is visible to later declarations
  and the body, but not to its own initializer. Empty declaration sequences work.
- `()` is an empty tuple; `(x)` is grouping; `(x,)` is a singleton tuple;
  `(x, y)` is a pair. Larger tuples and trailing commas are supported.
- `t.0` selects the first component; indices are nonnegative integer literals.
  Bounds and tuple type are checked during evaluation.
- `f(x)` passes one expression. `f(x, y)` passes **one tuple argument**;
  `f()` passes the empty tuple, and `f(x,)` passes a singleton tuple.
  `f(x)(y)` performs two successive applications.
- Calls and projections associate left to right: `f(x).0(y)` means
  apply `f` to `x`, project component zero, then apply that result to `y`.
- Unary `-e` becomes `0 - e`; unary `+e` becomes `e`.
- `/` uses integer floor division, as in the evaluator. Conditions require booleans.
- `list_nil()` creates an empty list. `list_nil` is reserved; this syntax
  produces `D0Eop0("list_nil")`, which evaluates to `D0Vlist(fnlist_nil())`.
- `list_cons(head, tail)` produces `D0Eop2("list_cons", head, tail)`.
  It evaluates both operands left to right and prepends the head value to the
  tail list. The head may be any value; the tail must evaluate to `D0Vlist`.
  `list_cons` is reserved. For example, `list_cons(1, list_cons(2, list_nil()))`
  creates a list containing 1 and 2.
- `list_nilq(xs)` produces `D0Eop1("list_nilq", xs)` and returns `true`
  when the list is empty, or `false` otherwise. Its operand must evaluate to
  `D0Vlist`. `list_nilq` is reserved.
- `list_head(xs)` and `list_tail(xs)` are reserved unary primitives returning
  the first value and remaining list. They raise `TypeError` for a non-list
  and `ValueError` for an empty list.

## List library
 
`print(value)` is a reserved unary primitive. It evaluates its operand once,
prints its readable representation followed by a newline, and returns `()`.
Integers and booleans print as `42` and `true`; tuples as `(1, false)`;
lists as `[1, 2]`; options as `optn_nil()` or `optn_cons(1)`.
Closures print as `<lam>` or `<fix>`. Nested values are formatted recursively.
To print a tuple, use `print((1, 2))`. To print the empty tuple, use `print(())`.
For example, `let ignored = print(42) in 0 end` prints `42` and returns zero.

`mylib/list.lam` contains sequential declarations for singleton, length, reverse,
append, concat, map, filter, left/right folds, exists, forall, take, drop, and
integer range. Comments in the file specify argument order and boundary cases.

```python
from pathlib import Path
from lambda2 import d0cls_parse, d0exp_parse, d0exp_evaluate, D0Elets

library = d0cls_parse(Path('mylib/list.lam').read_text())
expression = d0exp_parse('list_length(list_range(0, 5))')
value = d0exp_evaluate(D0Elets(library, expression))  # D0Vint(5)
```

The library uses the interpreter's recursive evaluation and is subject to
Python's recursion limit, including functions written with tail calls.

## Options

Options use `D0Voptn`, backed by `fnoptn[d0val]`. These reserved primitives
are available without loading a library:

- `optn_nil()` is a nullary operator creating an empty option.
- `optn_cons(value)` is a unary operator wrapping any value, including another option.
- `optn_nilq(opt)` returns whether the option is empty.
- `optn_get(opt)` extracts its value; an empty option raises `ValueError`.
  Both queries raise `TypeError` for non-option operands.

`mylib/optn.lam` adds presence/length queries, eager and lazy defaults, map,
bind, filter, fold, exists, forall, lazy fallback, and conversion to a list.
Load it with `d0cls_parse` and `D0Elets`, just like the list library.
It does not require `list.lam`. Argument order and callback requirements are
documented in the file. For example:

```lambda
optn_map(optn_cons(21), lam (x) => x * 2)
```

This evaluates to an option containing 42. Callbacks to `optn_bind` and
`optn_or_else` are expected to return options; the library does not dynamically
check that callback contract.

## Examples

Recursive factorial:

```text
let
  fact = fix f(x) =>
    if (x > 0) then x * f(x-1) else 1
in
  fact(5)
end
```

Factorial with a tuple accumulator (both examples evaluate to `D0Vint(120)`):

```text
let
  fact = lam (n) =>
    let
      loop = fix f(xr) =>
        let
          x = xr.0
          r = xr.1
        in
          if x < n then f(x+1, (x+1) * r) else r
        end
    in
      loop(0, 1)
    end
in
  fact(5)
end
```

The accumulator starts at zero; `loop(n, 1)` in `README.00` would immediately
return one. `README.00` is retained as the original design sketch.
