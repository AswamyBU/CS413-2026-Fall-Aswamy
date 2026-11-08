# Type-checking examples

These files use the annotated syntax implemented in `../lambda2.py`.

The well-typed programs are:

- `examples.lam`: recursive factorial and list sum, plus typed options/tuples.
- `higher_order.lam`: higher-order functions and tuple argument types.
- `let.lam`: sequential inferred bindings, local functions, and local recursion.
- `let_monomorphic.lam`: an inferred let-bound function reused at one type.
- `top_level_polymorphic.lam`: top-level inferred functions reused at multiple types.
- `list_option.lam`: a recursive list transformation and option handling.

The `type_error_*.lam` files each contain one intentional static type error:
an incorrect function argument, a non-boolean condition, mismatched branches,
a heterogeneous list, a recursive function body with the wrong result type, or
an attempt to use one monomorphic let-bound function at two types.

Top-level functions can declare type parameters, like mypy generic functions:
`identity[T] : T -> T = lam (x: T) => x`. Each use is instantiated separately,
so later declarations can use `identity` at both `int -> int` and `bool -> bool`.
The same explicit syntax works in local declaration blocks. Functions without
declared type parameters, including inferred local functions, remain monomorphic.

From the `LAMBDA` directory, check a valid example with:

```python
from pathlib import Path
from lambda2 import d0cls_parse, d0cls_typecheck

source = Path('mytest/higher_order.lam').read_text()
d0cls_typecheck(d0cls_parse(source))
```

To inspect an expected error, pass one of the `type_error_*.lam` sources to the
same checker; it raises `TypeCheckError` with the expected and actual types.
