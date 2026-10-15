# Java tests

From the assignment directory:

```sh
make -C JAVA/TEST test         # Both implementations
make -C JAVA/TEST test-direct  # Lambda1 only
make -C JAVA/TEST test-vp      # Lambda1_vp only
```

Inside this directory, use `make test`, `make test-direct`, or `make test-vp`.
Requires JDK 17+. Override executables with `JAVAC=... JAVA=...` if needed.
Compiled classes go in `.build/`. No JUnit, Python, or JavaScript runtime is needed.
A failed check causes a nonzero exit status; Java's `-ea` option is not required.

Each suite contains 70 named examples with explicit expected results matching
`../../TEST/cases.json`. These cover all expression forms, arithmetic and
comparisons, large integers, floor division, lexical and recursive closures,
higher-order functions, shadowing, pairs, free variables, eager evaluation,
left-to-right ordering, branch selection, and error cases. Expected values are
independent of either interpreter; these Java examples are maintained separately
from the JSON examples.

Additional checks cover explicit environments, unbound-variable sentinels,
immutable free-variable sets, unsupported expressions, and closure capture.
The visitor suite also checks direct visitor use, scope isolation when reusing a
visitor, and dispatch to a custom visitor.
