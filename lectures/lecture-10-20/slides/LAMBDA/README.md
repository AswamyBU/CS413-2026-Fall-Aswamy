# Typed LAMBDA

This directory contains an explicitly typed extension of the interpreter in
`lambda2.py`. Every binder has a type annotation: lambda parameters, both the
recursive function and parameter in `fix`, and each sequential `let` binding.
The checker is monomorphic: a let-bound function keeps one type, with no
polymorphic generalization.

## Types and annotations

```text
type ::= int | bool | unit | type -> type
       | (type, ..., type) | List[type] | Option[type]
```

Function arrows associate to the right. Tuples carry a type for every
component; `()` has type `unit`. Lists and options are homogeneous, even though
the underlying runtime value representation can contain arbitrary values.

```lambda
let
  below : int -> bool = lam (n : int) => n < 10
  answer : bool = below(7)
in
  answer
end
```

Recursive functions annotate the function and its parameter:

```lambda
let
  fact : int -> int = fix fact(n: int): int =>
    if n <= 1 then 1 else n * fact(n - 1)
in
  fact(5)
end
```

The same type is written on the let binding and the `fix` expression. The
checker confirms they agree, and checks the body against the declared result
type. A typed tuple/list example:

```lambda
let
  xs : List[int] = list_cons(10, list_cons(20, list_nil()))
  first : int = list_head(xs)
  pair : (int, bool) = (first, first < 15)
in
  pair.1
end
```

The empty `list_nil()` and `optn_nil()` constructors start with a fresh element
type. Their type is determined by surrounding uses or a declaration. For
example, `xs : List[int] = list_nil()` checks, while an unconstrained empty
list can retain an unresolved type variable.

## Using the checker

Python 3.12 or later is required, as in the original interpreter.

```python
from lambda2 import d0exp_parse_and_typecheck, d0exp_evaluate

expr, typ = d0exp_parse_and_typecheck(
    'let x : int = 6 in x * 7 end'
)
print(typ)                    # TInt()
print(d0exp_evaluate(expr))   # D0Vint(arg1=42)
```

Run the type-checker tests from this directory with
`python3 -m unittest discover -s TEST -v`.

`d0exp_typecheck(ast)` checks an already built expression. It raises
`TypeCheckError` (a `TypeError` subclass) on an unbound variable, annotation
mismatch, or invalid operation. To get readable type names, use
`format_type(typ)`. Run the checker before the evaluator; the evaluator
preserves the original dynamic checks and does not implicitly type-check.

The checker supports integers, booleans, conditionals, annotated lambdas and
recursive functions, sequential annotated declarations, application, tuples
and projections, homogeneous lists, homogeneous options, and all existing
primitive operators. List and option callbacks are checked through ordinary
function types. This is a simple monomorphic type system; it does not infer
types for bound variables or support polymorphic functions.

## Example program

[`examples.lam`](examples.lam) is a complete declaration sequence. It defines
factorial and a recursive list sum, then combines their results with a typed
option and tuple. Load and check it before evaluating its `report` binding:

```python
from pathlib import Path
from lambda2 import D0Elets, D0Evar, d0cls_parse, d0cls_typecheck
from lambda2 import d0exp_evaluate, d0val_format

decls = d0cls_parse(Path('examples.lam').read_text())
d0cls_typecheck(decls)
report = d0exp_evaluate(D0Elets(decls, D0Evar('report')))
print(d0val_format(report))  # (120, 12, true)
```
