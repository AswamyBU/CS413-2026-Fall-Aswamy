# CS413 lecture slides

- `pytest.tex` / `pytest.pdf`: pytest lecture (28 slides), including a
  free-variable testing exercise and discussion.
- `examples/pytest_demo/`: runnable stack, resource, and expression tests.

- `unittest.tex` / `unittest.pdf`: unittest lecture (27 slides).
- `examples/unittest_demo/`: standalone standard-library examples.

Run `make` to rebuild all Beamer PDFs, or `make pytest.pdf` for the pytest
lecture. Requires LaTeX with Beamer, listings, lmodern, amsmath, and booktabs.
Build intermediates go in `.build/`, which Git ignores.

## pytest lecture

Designed for a roughly 50-minute lecture with a short exercise. Assumes
Python functions, classes, exceptions, and basic lambda-calculus syntax.

From `examples/pytest_demo/`, set up and run the examples:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest
python -m pytest -q
```

Alternatively, run `make test-pytest` with pytest installed for `python3`.
The skip/xfail slide is illustrative, so its placeholder tests are not part
of the runnable suite. The expression example is standalone and does not
require the earlier interpreter.

Suggested pacing: motivation and first tests (12 minutes), parametrization
and fixtures (15), side effects and other assertions (10), expression
exercise and discussion (8), testing workflow and questions (5).

The slides link to the official pytest documentation. Additional references:
[invocation](https://docs.pytest.org/en/stable/how-to/usage.html),
[output capture](https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html),
and [skip/xfail](https://docs.pytest.org/en/stable/how-to/skipping.html).

## unittest lecture

A roughly 50-minute introduction to Python's built-in testing framework,
using the same stack and expression examples as the pytest lecture. Covers
TestCase, discovery, assertions, setup and cleanup, subTest, temporary files,
output capture, unittest.mock, and a free-variable exercise.

Build with `make unittest.pdf`. Run `make test-unittest`, or:

```sh
cd examples/unittest_demo
python3 -m unittest -v
```

No third-party dependencies are needed. Examples were checked with Python
3.12. The suite makes no network requests: it patches the service dependency.
Skip and expectedFailure snippets are illustrative and are not runnable tests.
The suite has 13 test methods; subTest cases do not increase that method count.
Run `make test` for both example suites (requires pytest for its examples).

Suggested pacing: first tests and discovery (12 minutes), assertions and
fixtures (15), subtests and controlled dependencies (13), exercise and
comparison with pytest (10).

References: [unittest](https://docs.python.org/3/library/unittest.html) and
[unittest.mock](https://docs.python.org/3/library/unittest.mock.html).
