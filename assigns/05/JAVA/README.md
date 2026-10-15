# Java lambda interpreters

Requires JDK 17 or later. No external libraries are needed.

- `Lambda1.java` translates `../lambda1.py` using direct expression dispatch.
- `Lambda1_vp.java` translates `../lambda1_vp.py` using generic visitors and `accept`.

Both expose nested expression, value, and environment classes, plus static
`d0exp_evaluate`, `d0exp_fvset`, and `d0env_search` methods. Integers use
`BigInteger` with convenience constructors accepting `long`. Free-variable sets
and environment links are immutable. Invalid operand types raise
`IllegalArgumentException`; division by zero raises `ArithmeticException`.

Run from the assignment directory:

```sh
make -C JAVA/TEST test
```

See [TEST/README.md](TEST/README.md) for individual test targets.
