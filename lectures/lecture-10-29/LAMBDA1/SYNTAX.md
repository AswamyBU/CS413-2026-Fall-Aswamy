# LAMBDA concrete syntax

The parser and evaluator are in `lambda2.py` (Python 3.12 or later). This
document describes the implemented **annotated** syntax. `d0exp_parse` parses
one complete expression; `d0cls_parse` parses zero or more sequential value
declarations. Parsing builds an AST and does not evaluate or type-check it.
Malformed input raises `LambdaSyntaxError`, a `SyntaxError` subclass with
line and column information.

```python
from lambda2 import d0exp_parse, d0exp_evaluate

value = d0exp_evaluate(d0exp_parse('let x = 6 in x * 7 end'))
# D0Vint(arg1=42)
```

## Grammar

Here `{ ... }` means repetition, `[ ... ]` means optional, and quoted strings
are literal tokens. A declaration may end with an optional semicolon. The
initializer expression ends where the next declaration or the enclosing
`in`/end of input begins.

```text
declarations   = { identifier ["[" type-parameter {"," type-parameter} "]"]
                   [":" type] "=" expression [";"] } ;
expression     = "lam" "(" identifier [":" type] ")" "=>" expression
               | "fix" identifier "(" identifier [":" type] ")" [":" type]
                   "=>" expression
               | "if" expression "then" expression "else" expression
               | "let" declarations "in" expression "end"
               | comparison ;
comparison     = additive [ comparison-op additive ] ;
comparison-op  = "<" | ">" | "<=" | ">=" | "==" | "!=" ;
additive       = multiplicative { ("+" | "-") multiplicative } ;
multiplicative = unary { ("*" | "/") unary } ;
unary          = ("+" | "-") unary | postfix ;
postfix        = atom { call | projection } ;
call           = "(" [ expression { "," expression } [","] ] ")" ;
projection     = "." integer ;
atom           = integer | "true" | "false" | identifier | tuple-or-group
               | "list_nil" "(" ")" | "optn_nil" "(" ")"
               | "list_cons" "(" expression "," expression ")"
               | ("list_nilq" | "list_head" | "list_tail" | "optn_cons"
                  | "optn_nilq" | "optn_get" | "print") "(" expression ")" ;
tuple-or-group = "(" [ expression [":" type | "," [ expression { "," expression } [","] ]] ] ")" ;
type           = type-atom ["->" type] ;
type-atom      = "int" | "bool" | "unit" | "List" "[" type "]"
               | "Optn" "[" type "]" | "(" [type {"," type} [","]] ")" ;
type-parameter = identifier ;
```

Identifiers match `[A-Za-z_][A-Za-z_0-9]*`. Keywords and primitive names are
reserved and case-sensitive. Integers are nonnegative decimal tokens; negative
expressions use unary minus. Whitespace, including newlines, is insignificant;
`#` starts a comment through the end of the line. Bare juxtaposition is not
application. Empty declaration sequences are accepted. Type annotations on
let declarations, lambda parameters, and the parameter and result of `fix` are
optional. Omitted binder types are inferred by the type checker. Type variables
are names declared in a function declaration's `[T, ...]` parameter list;
they are valid in that declaration's signature and body only.

## Meaning and precedence

From strongest to weakest: calls and projections, unary signs, multiplication
and division, addition and subtraction, comparisons. Arithmetic operators are
left-associative; comparisons cannot be chained. Parentheses override
precedence. `lam`, `fix`, `if`, and `let` parse their bodies as full
expressions. Parenthesize one when it is intended as an arithmetic operand or
as the function expression in a call.

- `lam (x [: T]) => body` creates a one-argument function; an omitted `T` is
  inferred from how `x` is used.
- `fix f(x [: T]) [: U] => body` binds both `f` and `x` in `body`; omitted
  parameter and result types are inferred from the body and recursive calls.
- `let x [: T] = e1 y [: T2] = e2 in body end` creates sequential bindings.
  Each initializer is evaluated before its name is bound, and each name is
  visible to later declarations and the body. A binding is monomorphic unless
  it is a function with explicitly declared type parameters and a signature.
  Such a function is checked at that signature and instantiated at each use;
  inferred types are never generalized. Annotations are checked by the checker.
- `()` is the empty tuple; `(x)` is grouping; `(x,)` is a singleton tuple;
  `(x, y)` and larger forms are tuples. A trailing comma is accepted.
- `(expression : T)` annotates an expression with type `T`; the type checker
  verifies that the expression has that type.
- `t.0` selects the first tuple component. The index must be a nonnegative
  integer literal; tuple shape and bounds are checked by the type checker when
  it is used, and by the evaluator when evaluating an unchecked AST.
- `f(x)` passes one expression. `f(x, y)` passes one tuple argument;
  `f()` passes the empty tuple, and `f(x,)` passes a singleton tuple.
  `f(x)(y)` performs two successive applications. Calls and projections
  associate left to right: `f(x).0(y)` applies `f`, projects component zero,
  then applies that result to `y`.
- Unary `-e` is represented as `0 - e`; unary `+e` is represented as `e`.
  `/` uses integer floor division. Conditions require booleans at runtime and
  in type-checked expressions.

`list_nil()` and `optn_nil()` create empty lists and options. `list_cons(h, t)`
prepends a value to a list; `list_nilq`, `list_head`, and `list_tail` inspect
lists. `optn_cons(x)`, `optn_nilq`, and `optn_get` construct and inspect
options. `print(x)` prints a readable representation plus a newline and
returns `()`. These names are reserved primitives, not ordinary variables.
The evaluator checks primitive operand shapes dynamically; the type checker
also enforces homogeneous list/option types, integer arithmetic, and the
declared function and tuple types. `list_head`/`list_tail` on an empty list and
`optn_get` on an empty option raise `ValueError`.

`d0val_format` formats values as readable text: integers and booleans as
`42` and `true`, tuples as `(1, false)`, lists as `[1, 2]`, options as
`optn_nil()` or `optn_cons(1)`, and closures as `<lam>` or `<fix>`. Nested
values are formatted recursively.

## Examples

Recursive factorial, with an inferred parameter type and result type:

```lambda
let
  fact : int -> int = fix f(x) =>
    if x > 0 then x * f(x - 1) else 1
in
  fact(5)
end
```

An accumulator with a tuple argument:

```lambda
let
  fact : int -> int = lam (n : int) =>
    let
      loop : (int, int) -> int = fix f(xr : (int, int)) : int =>
        let
          x = xr.0
          r = xr.1
        in
          if x < n then f(x + 1, (x + 1) * r) else r
        end
    in
      loop(0, 1)
    end
in
  fact(5)
end
```

Let-bound functions are monomorphic. The following uses `id` at one type and
is accepted:

```lambda
let id = lam (x) => x in id(42) end
```

Using the same binding at both `int` and `bool` is rejected:

```lambda
let id = lam (x) => x in (id(42), id(true)) end
```
