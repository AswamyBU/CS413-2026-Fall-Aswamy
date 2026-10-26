# Midterm 1 (Assignment 6): Compiling Extended LAMBDA into Pure Lambda-Calculus

This project compiles extended LAMBDA source ASTs (numbers, booleans,
arithmetic, comparisons, `if`, `let`, pairs, `and`/`or`/`not`, and recursion)
into Church's pure lambda-calculus. The output uses only variables,
one-parameter lambdas, and applications. A single call-by-value evaluator runs
both the source programs and the compiled terms, and bounded observers decode
the compiled results so they can be checked against the expected answers.

Translation rules, the predecessor construction, the naming policy, the
evaluation strategy, and the correctness argument are in [DESIGN.md](DESIGN.md).

## Requirements

- **Python 3.12 or later.** The supplied `lambda1_vp.py` uses `type` aliases.
  I developed and tested this project with Python 3.14.0.
- **No third-party dependencies.** Only the standard library is used
  (`unittest`, `dataclasses`, `argparse`, ...).
- The supplied file `assigns/05/lambda1_vp.py` is imported unchanged, so it
  must stay at that path. `source_syntax.py` adds `assigns/05` to `sys.path`.

## Setup, tests, and demo

There is nothing to install. Run every command from **`assigns/06/`**
(`python3` may be the interpreter name on macOS/Linux):

```sh
# full automated test suite (113 tests)
python -m unittest discover -s MySolution/TEST -v

# the demonstration: all 14 required examples plus 6 extra ones
python MySolution/demo.py

# useful demo options
python MySolution/demo.py --mandatory                  # only DEMO-01 .. DEMO-14
python MySolution/demo.py --only DEMO-10 DEMO-11       # selected examples
python MySolution/demo.py --exec-budget 500 --obs-budget 100
python MySolution/demo.py --no-save                    # don't write generated/
```

For each example, `demo.py` prints:

- the source program
- the generated pure term (inline if it is at most 400 characters)
- the shared evaluator's answer on the source AST
- the execution status and beta-value step count
- the observation status and its own step count
- the decoded answer and the explicit expected answer
- PASS or FAIL

Every generated term is also saved as `MySolution/generated/<ID>.txt`. The
command exits with status 0 only if every example matches.

## Module overview

| File | Contents |
| --- | --- |
| `target.py` | Target AST `Var` / `Lam` / `App`, printer `show`, free variables, all names, capture-avoiding `substitute`, `alpha_equiv`, `is_pure`, `fresh_name` |
| `church.py` | Closed Church-encoding combinators: booleans, numerals, `SUCC`, `PRED`, `IS_ZERO`, `ADD`, `SUB`, `MUL`, comparisons, `NOT`/`AND`/`OR`, pairs, `Z` |
| `source_syntax.py` | Imports the supplied source AST; source printer and substitution (adapted from my Assignment 5); converts source values to Python data |
| `compiler.py` | `CompileVisitor` (a `D0ExpVisitor`) and `compile_expr(source) -> Term`; `CompileError` |
| `evaluator.py` | The one shared evaluator: `evaluate(expr, budget=None, *, trace=None) -> EvalResult` for source ASTs and target terms |
| `observe.py` | Bounded observers for naturals, booleans, and (nested) pairs |
| `pipeline.py` | `run_program` (compile, then execute, then observe) and `source_result` |
| `examples.py` | The source programs for the demonstrations (`DEMO-01` .. `DEMO-14`, `EXTRA-1` .. `EXTRA-6`) |
| `demo.py` | The command-line demonstration |
| `TEST/` | `unittest` suite: `test_target`, `test_evaluator`, `test_church`, `test_compiler`, `test_observe`, `test_demos`, plus `helpers.py` |
| `generated/` | Pure terms written by the last `demo.py` run |
| `slides.pdf`, `slides.html` | Presentation slides and their editable source |

The evaluator does not import the compiler or the Church library. The compiler
does not import the evaluator. The only place they meet is `pipeline.py`.

## Budgets

Execution and observation have **separate** budgets and separate step counts.
Both are counted in beta-value steps.

| Budget | Default in `demo.py` | Used by the tests |
| --- | --- | --- |
| Execution (running the compiled program to a value) | 10,000 | 20,000 (3,000 for programs expected to diverge) |
| Observation (decoding the value, including pair projections) | 10,000 | 20,000 |

These numbers are generous. The most expensive terminating demo is Fibonacci 5,
which needs 2,021 execution steps. The most expensive observation is
factorial 4, which needs 218 steps. Here are the step counts from the demo:

| ID | Program | Exec steps | Obs steps | Decoded |
| --- | --- | --- | --- | --- |
| DEMO-01 | `2 + 3 * 4` | 4 | 25 | 14 |
| DEMO-02 | `2 - 5` | 87 | 2 | 0 |
| DEMO-03 | `if 2 <= 3 then 7 else 9` | 77 | 9 | 7 |
| DEMO-04 | `let x = 3 in (lam y. x + y) 4` | 4 | 13 | 7 |
| DEMO-05 | `fst (pair 2 true)` | 6 | 4 | 2 |
| DEMO-06 | `snd (pair 2 true)` | 6 | 2 | true |
| DEMO-07 | `(lam f. f 3) (lam x. x + 1)` | 4 | 10 | 4 |
| DEMO-08 | `if true then 1 else LOOP` | 3 | 3 | 1 |
| DEMO-09 | `(lam x. 0) LOOP` | exhausted at 10,000 | none | none |
| DEMO-10 | factorial 4 | 471 | 218 | 24 |
| DEMO-11 | Fibonacci 5 | 2,021 | 45 | 5 |
| DEMO-12 | `LOOP` | exhausted at 10,000 | none | none |
| DEMO-13 | `true and false` | 3 | 2 | false |
| DEMO-14 | `false or true` | 3 | 2 | true |

Exhausting the budget only means that more steps were needed. It does not
prove that a program runs forever.

## Statuses and diagnostics

- **Compilation** returns a `Term` or raises `CompileError`. The error message
  names the unsupported thing, for example `unsupported negative integer
  literal -3 ...` or `unsupported binary operator '/' in (4 / 2) ...`.
  Unsupported forms are rejected anywhere in the tree, including unselected
  branches and function bodies that are never called.
- **Evaluation** returns `EvalResult(status, value, steps, budget)`. The
  `status` is either `"value"` (and `value` holds the lambda or source value)
  or `"exhausted"` (and `value` is `None`). `steps` is the number of
  beta-value steps actually performed. `EvalError` is raised for a source
  run-time error (type error, unbound variable, unsupported literal or
  operator) and for **open target terms**: target execution is limited to
  closed terms. Compilation and substitution still work on open terms.
- **Observation** returns `Observation(status, value, steps, detail)`:
  - `"ok"`: `value` is an `int`, `bool`, or nested `tuple`.
  - `"exhausted"`: the observation budget ran out.
  - `"malformed"`: the observation context finished, but the result had the
    wrong shape for the requested kind. `detail` says what was found.

  The caller always passes the expected kind (`NAT`, `BOOL`, or
  `pair_kind(k1, k2)`), because `NUM(0)` and `FALSE` are the same term.

## Test coverage checklist

| Assignment testing obligation | Where it is tested |
| --- | --- |
| 1. Substitution with shadowing and capture hazards (`(lam y. x)[x := y]`), independently of execution | `test_target.SubstitutionTests` (ACC-01, nested capture, shadowing, FV law, inputs and replacement preserved) |
| 2. Left-to-right CBV, no reduction under lambdas, zero-step values, determinism, budget exhaustion | `test_evaluator.TargetReductionTests` (ACC-02 trace of `(I1 I2) (I3 I4)`, ACC-03 budget boundaries, ACC-04 determinism and input snapshot, Omega exhaustion) |
| 3. Every constructor and operator; zero, pred 0, equal/unequal operands, both outcomes of each comparison, both booleans, truth tables | `test_compiler.ConstructorTests`, `OperatorTests`; `test_church` (each encoding on its own, ACC-05) |
| 4. Nested lets and lambdas, let-initializer scope, both fix binders, coincident binders, open expressions, encoding-name collisions, FV preservation, immutability | `test_compiler.ScopeTests` (ACC-06, ACC-07), `StructuralPropertyTests` (400 random open ASTs) |
| 5. Unselected divergence skipped; divergent arguments, let initializers, and either pair component exhaust | `test_demos.DelayedBranchTests`, `StrictPositionTests` (ACC-08) |
| 6. All demonstrations, nested pairs, rejection of negative literals and unsupported operators, even in unselected branches | `test_demos.MandatoryDemonstrationTests`, `test_observe.PairObserverTests` (ACC-12), `test_compiler.RejectionTests` (ACC-09) |
| 7. Output uses only the three constructors; library combinators are closed; compilation never calls the evaluator | `StructuralPropertyTests` (ACC-10, with the evaluator replaced by failing test doubles), `test_church.LibraryShapeTests` |
| Observers: alpha-renamed and computed values, malformed outputs, observation exhaustion, zero under both kinds | `test_observe` (ACC-11) |
| Printer formats | `test_target.PrinterTests` (ACC-13) |
| Compiled answers agree with source answers | `test_compiler.DifferentialTests` (120 random well-typed programs) |
| One evaluator for both languages; evaluator does not import the compiler | `test_evaluator.SharedEvaluatorStructureTests` |

## Recording

- **Recording (15–20 min, with my face visible):**
  <https://drive.google.com/file/d/1jtRdvPIX0owcFp0Nbmh1pBswc9YDHlsb/view?usp=sharing>

## Limitations

- **Speed.** Evaluation uses substitution and Church numerals are unary, so
  cost grows quickly with the size of the numbers. `EQ`/`LEQ` cost `O(m·n)`
  steps, and factorial or Fibonacci of much larger inputs need much larger
  budgets.
- **Closed terms only.** Target execution and decoding only work on closed
  terms. Open terms are rejected with `EvalError`.
- **No type checking.** Programs are assumed to be well-typed. An ill-typed
  program (for example `1 + true`) still compiles, and its compiled result
  means nothing. The source path of the evaluator does report it as an
  `EvalError`.
- **Weak malformed-output detection.** The observers check the final shape
  only. Some lambdas that are not numerals still decode as numbers, for
  example `lam x. x` decodes as `1`. The assignment does not require
  recognizing every invalid encoding.
- **Long printed terms.** The printed form repeats every library combinator in
  full, so terms get long (factorial is about 1,500 characters). That is why
  longer ones are saved to files instead of printed.
- **Recursion depth.** Substitution and free-variable computation are
  recursive, so they depend on how deeply terms are nested. The demos are
  nowhere near Python's recursion limit. The evaluator loop and the printer
  are iterative.

## Attribution

- `source_syntax.py` adapts the pretty printer, name collector, `FreshNames`,
  and substitution visitor from my Assignment 5 solution
  (`assigns/05/MySolution/lambda1_visitors.py`). The alpha-renaming policy in
  `target.substitute` follows the same design.
- The source AST and `D0ExpVisitor` are from the supplied
  `assigns/05/lambda1_vp.py`, which is unchanged.
- Encodings: Church booleans, numerals, pairs, and the pair-based (Kleene)
  predecessor follow B. C. Pierce, *Types and Programming Languages*, ch. 5,
  and the Wikipedia article "Church encoding". The `Z` combinator and the
  `STEP`/`BASE` observation context are as given in `Assign06.md`.
- AI assistance is described in [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md).
- This is an individual submission.
