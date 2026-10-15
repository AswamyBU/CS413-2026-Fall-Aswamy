# Visitor interpreter tests

Run from the assignment directory with Python 3.12+ and Node.js 18+:

```sh
make -C TEST test         # Run Python tests (also the default target).
make -C TEST test-py      # Run Python tests explicitly.
make -C NODE/TEST test    # Run JavaScript tests.
```

Inside `TEST`, use `make test` or `make test-py` for Python tests.
Inside `NODE/TEST`, use `make test` for JavaScript tests.
Override runtimes if needed with `make -C TEST test PYTHON=python3.12`
or `make -C NODE/TEST test NODE=node`.
The equivalent direct commands are:

```sh
python3 -m unittest discover -s TEST -p 'test_*.py' -v
node --test NODE/TEST/test_lambda1_vp.js
```

No third-party dependencies are needed. Both commands return a nonzero exit
status if a test fails. Paths inside the tests are relative to the test files.

`cases.json` supplies shared examples with explicit expected values and free
variables. Expressions use arrays such as `["op2", "+", ["int", "2"], ["int", "3"]]`.
Integer literals and expected integer values are decimal strings to preserve
precision when JavaScript reads JSON. Cases with only `fv` test analysis without
evaluation. Division-by-zero cases expect Python `ZeroDivisionError` or JavaScript
`RangeError`; invalid operand types expect `TypeError` in both languages.

Coverage includes all expression forms and operators, signed floor division,
large integers, lexical closures, higher-order functions, recursive functions,
shadowing, eager left-to-right evaluation, conditional branch selection, pairs,
unbound variables, and free-variable binding rules. Each language also tests
explicit environments, immutability, direct visitor use, and closure capture.
JavaScript additionally tests integer input validation and independent Set results.

JavaScript sources and tests live in `../NODE`; run them independently with
`make -C NODE/TEST test` from the assignment directory.
