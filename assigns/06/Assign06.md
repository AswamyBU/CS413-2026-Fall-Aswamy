# CS413 Midterm 1 Project

## Compiling Extended LAMBDA into Pure Lambda-Calculus

## Due date and project arrangements

**Due: Sunday, October 25, 2026.**

Please keep everything you submit in `assigns/06/MySolution/`.

## Objective

Build a compiler that translates an extended lambda-calculus with
numbers, booleans, arithmetic, conditionals, pairs, local bindings,
and recursion into Church's pure, untyped lambda-calculus. The
generated program must contain only variables, single-parameter lambda
abstractions, and applications.

Execute generated programs with a beta-reduction engine and show that their
decoded results agree with expected source-language results. Use one evaluator
for both source ASTs and target terms. The target language is the variable,
lambda, and application subset of the source language, represented by its own
target AST. Your compiler must translate programs, not evaluate them and
encode their answers. This project brings together ASTs, visitors,
lexical scope, capture-avoiding substitution, modular design, and
automated testing.

## Starting point and scope

Use **Python 3.12 or later** and the source AST and `D0ExpVisitor`
interface in [Assignment 5's lambda1_vp.py](../05/lambda1_vp.py). Do
not modify that file.  Implement compilation as a visitor. You may
adapt your Assignment 5 work on printing, substitution, and fresh
names, with attribution.

The required deliverables are a compiler library, a target reducer, tests,
and a command-line demonstration. A web interface (for instance, through a
form of integration with Assignment 4) is optional.

Note that you do NOT have to have a parser (like the one given in
lectures/lecture-10-20).

### Source language

Support the following subset of the supplied AST:

| Source constructor | Required meaning |
| --- | --- |
| `D0Eint(n)` | Natural number: `n >= 0` |
| `D0Ebtf(b)` | Boolean `true` or `false` |
| `D0Evar(x)` | Variable |
| `D0Elam(x, body)` | Function abstraction |
| `D0Eapp(fn, arg)` | Function application |
| `D0Eop1("not", e)` | Boolean negation |
| `D0Eop2(op, e1, e2)` | Operations specified below |
| `D0Eif0(c, t, f)` | Boolean conditional: choose `t` if `c` is true, otherwise `f` |
| `D0Elet(x, init, body)` | Nonrecursive local binding |
| `D0Epair(e1, e2)` | Ordered pair |
| `D0Epfst(e)`, `D0Epsnd(e)` | First and second projection |
| `D0Efix(f, x, body)` | Recursive function with function name `f` and parameter `x` |

Required binary operators are natural-number `+`, truncated natural-number
subtraction `-`, `*`, `<`, `<=`, `>`, `>=`, `==`, and `!=`, and boolean `and`
and `or`. Subtraction satisfies `m - n = max(m - n, 0)`. Equality and
comparisons operate on natural numbers only. Despite its constructor name,
`D0Eif0` tests a boolean, not numeric zero.

Boolean conjunction and disjunction are required LAMBDA expressions, written
as `D0Eop2("and", e1, e2)` and `D0Eop2("or", e1, e2)`, respectively.
Both take boolean operands and return a boolean. Conjunction evaluates its
right operand only when the left operand is true; disjunction evaluates its
right operand only when the left operand is false.

Negative literals, division, and other operator spellings are outside this
project's source language. Reject them with a useful compilation error,
including when they occur in an unused branch or function body. Check source
forms throughout the AST without executing the program. You may assume valid
constructor argument shapes and well-typed uses of the supported operations;
static type checking and runtime type-error preservation are not required.

Use the identifier convention from Assignment 5:
`[A-Za-z_][A-Za-z0-9_]*`. A lambda binds its parameter in its body. A let binds
its name only in its body, not its initializer. A fix binds both names in its
body; if the names coincide, the parameter shadows the function name throughout
the body, so references resolve to the parameter and the function-name binding
has no effect there.

### Evaluation strategy

Implement one evaluator that accepts either a source AST or a target term; do
not implement or delegate to a separate source evaluator. The target AST has
the same variable, lambda, and application cases as the source AST, so the
evaluator handles target terms using those cases and handles source-only
constructors with their source-language rules. Apply left-to-right
call-by-value in both languages. Evaluate a function and then its argument
before application, and evaluate a let initializer before its body.
Evaluate both pair components, left before right, before constructing the
pair. Arithmetic and comparisons evaluate their operands left to right.

A conditional evaluates its condition and only the selected branch. Boolean
`and` and `or` short-circuit left to right. The compiler must implement these
control constructs with delayed branches (lambda thunks) and explicitly force
only the selected thunk. This does not change the target's call-by-value rule.
Use a call-by-value fixed-point combinator for recursion.

Thus `(lam x. 0) LOOP` exhausts any finite evaluation budget when `LOOP`
diverges, while `if true then 1 else LOOP` returns one. Use this evaluator to
obtain source-side expected results and to run compiled target terms; compare
the source results with observations of the corresponding target results.
Source-side evaluation is required only for terminating examples and need not
be step-bounded. For divergent examples, compile the source AST and use the
target evaluator's step budget to report exhaustion.

## Task 1: Represent and reduce pure lambda terms

Define a separate target AST with exactly these three forms:

```text
Term ::= Var(name) | Lam(name, Term) | App(Term, Term)
```

Target variable names use the same identifier convention as source names.
Compiler-generated binders must be chosen deterministically and fresh against
all names in the translated terms they surround, including source free
variables; this prevents capture even when a source variable is named like a
common encoding variable.

Provide a printer using `x`, `(lam x. body)`, and `(fn arg)`. Multi-argument
notation in your report is shorthand for nested single-argument abstractions
or applications. Generated ASTs must use the three forms above exclusively.

Implement free-variable analysis, capture-avoiding substitution, and a
**weak, left-to-right call-by-value evaluator** for the target AST. Values are
lambda abstractions. This is the variable, lambda, and application subset of
the shared evaluator; source-only constructors use source-language values and
operations.
A beta-value step is:

```text
(lam x. body) v  -->  body[x := v]    where v is a lambda abstraction
```

In an application, evaluate the function first, then the argument, then
substitute the argument value into the function body. Do not evaluate beneath
lambda abstractions or perform eta reduction. A lambda is a completed value
even if its body contains redexes. When evaluating a target term, the evaluator
operates only on the target AST and applies no source-language operations.
Execution may be restricted to closed target terms; compilation and
substitution must still support open terms. Document rejection of open terms
if target execution is restricted to closed terms.

Accept a configurable nonnegative maximum number of beta-value steps. Report
completion with the resulting value or step-budget exhaustion, and the number
of steps performed. A value completes with zero steps, including with budget
zero. A value reached on the last permitted step counts as completed.
Exhaustion means another evaluation step is needed but the budget is spent;
it is not a proof of nontermination. Do not mutate input terms. The evaluator
must accept a configurable step budget for target terms and count beta-value
steps as specified here. Source-side results and errors must follow the
specified source-language rules.

## Task 2: Build a Church-encoding library

Implement target-AST builders for natural numbers, booleans, pairs, arithmetic,
comparisons, boolean operations, and recursion. Use these representations:

```text
TRUE     = lam t. lam f. t
FALSE    = lam t. lam f. f
NUM(n)   = lam s. lam z. s applied n times to z
PAIR     = lam a. lam b. lam p. p a b
Z        = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
```

Thus `NUM(0) = lam s. lam z. z` and
`NUM(2) = lam s. lam z. s (s z)`. Implement successor, predecessor, zero test,
addition, truncated subtraction, multiplication, the required comparisons,
negation, conjunction, disjunction, and pair projections. Predecessor of zero
must be zero. You must explain your predecessor construction in the report.

Names such as `TRUE`, `PAIR`, and `Z` are documentation abbreviations and
Python builder names, not target-language primitives. Expand them into pure
terms in compiler output. Each library combinator must be closed.

Python arithmetic may construct a numeral from a source literal and inspect
a decoded result in tests. It must not implement the arithmetic of a generated
program. The reducer must not recognize Church encodings and replace their
evaluation with Python operations.

## Task 3: Implement the compiler

Expose an entry point equivalent to:

```text
compile_expr(source_expression) -> target_term
```

Compilation must be compositional: translate subexpressions and combine
their translations according to their source constructors. Do not invoke
the shared evaluator during compilation. Even a diverging
source program must compile without trying to execute it.

In `DESIGN.md`, give a translation rule for every required constructor and
operator. Use `C[e]` for the translation of `e`. These rules establish the
intended style:

```text
C[x]                 = x
C[lam x. e]          = lam x. C[e]
C[e1 e2]             = C[e1] C[e2]
C[let x = e1 in e2]  = (lam x. C[e2]) C[e1]
C[if c then t else f]= (C[c] (lam u. C[t]) (lam v. C[f])) I
C[fix f(x). e]       = Z (lam f. lam x. C[e])
```

Here `I = lam w. w` is a closed dummy value, and `u` and `v` are fresh,
unused thunk parameters. Expand `I` and `Z` into pure terms. Compile `and` and
`or` using the same delayed-branch mechanism. Ordinary `Y` unfolds forever
under call-by-value and is unsuitable here.

Supply the remaining rules yourself. Respect lexical scope, including
shadowing and coincident fix binders. Generated binders must not capture
source variables. Use a documented deterministic fresh-name policy wherever
you introduce binders around translated terms. Do not reserve common source
names such as `s`, `z`, `t`, `f`, or `x` for compiler use.

Compilation must work for open as well as closed expressions and preserve
their free-variable sets: `FV(C[e]) = FV(e)`, where `FV` respects the stated
lexical binding rules (including fix binding and coincident-name shadowing).
Execution and decoding examples may be restricted to closed programs.
Preserve the input source AST.

## Task 4: Decode results and demonstrate the pipeline

Provide bounded observers for Church naturals and booleans. A returned
lambda may contain unevaluated redexes, so structural matching against a
fully normalized Church numeral is insufficient. The caller supplies the
expected kind: `NUM(0)` and `FALSE` have the same lambda representation.

Use pure target observation contexts evaluated by the same call-by-value
engine. One permitted natural-number observation applies the result to
`STEP = lam tail. lam c. lam z. c tail` and `BASE = lam c. lam z. z`.
This builds a finite spine whose nodes can be counted structurally in Python,
up to alpha-renaming, without evaluating under lambdas. Boolean observation
applies the result to two distinct closed marker values and recognizes the
selected marker. Document your contexts and output shapes. Reject malformed
observation outputs and distinguish observation-budget exhaustion from
successful decoding; recognizing every invalid untyped encoding is not required.
Python may inspect these final data shapes but may not execute generated
arithmetic or replace target reduction with host computation.

To inspect a pair, first evaluate it to a value, then apply each Church
projection and evaluate the resulting terms under a step budget. Observe each
component using its expected kind, recursively for nested pairs. Evaluate
recursive functions only to lambda values before application, never beneath
their binders. Document separate execution and observation budgets and counts.

Provide one documented command that runs a collection of source AST examples
through compilation, target reduction, and decoding. Show the source,
generated pure term (or a saved file containing it), execution reduction
outcome and beta-value step count, observation outcome and its separate
beta-value step count, decoded answer, and explicit expected answer. Report
execution and observation budgets separately. No source parser is required;
examples may be built directly in Python.

Include at least these demonstrations. The notation below is explanatory,
not a required input syntax; `LOOP` denotes `(fix loop(x). loop x) 0`.

| Source example | Expected result |
| --- | --- |
| `2 + 3 * 4` | `14` |
| `2 - 5` | `0` |
| `if 2 <= 3 then 7 else 9` | `7` |
| `let x = 3 in (lam y. x + y) 4` | `7` |
| `fst (pair 2 true)` | `2` |
| `snd (pair 2 true)` | `true` |
| `(lam f. f 3) (lam x. x + 1)` | `4` |
| `true and false` | `false` |
| `false or true` | `true` |
| `if true then 1 else LOOP` | `1` |
| `(lam x. 0) LOOP` | Step-budget exhaustion |
| Recursive factorial applied to `4` | `24` |
| Recursive Fibonacci applied to `5`, with `fib(0)=0`, `fib(1)=1` | `5` |
| `LOOP` | Step-budget exhaustion |

Choose and document sufficient budgets for the terminating examples. No
particular step count or running-time threshold is prescribed.

## Testing and correctness argument

Use `unittest` for an automated suite with explicit expected results.
Include:

1. Target substitution with shadowing and capture hazards; for example,
   substituting `x := y` in `lam y. x` must produce an alpha-equivalent
   of `lam fresh. y`. This tests substitution independently of closed execution.
2. Left-to-right call-by-value traversal, no reduction under lambdas, zero-step values,
   deterministic reduction, and budget exhaustion on a diverging term.
3. Every required source constructor and operator. Include zero, predecessor
   of zero, equal and unequal operands, both outcomes of every comparison,
   both booleans, and all boolean operator truth-table cases.
4. Nested lets and lambdas, let-initializer scope, both fix binders, coincident
   fix binders, open expressions, and source names that collide with typical
   encoding names. Verify free-variable preservation and input immutability.
5. Unselected divergence in conditionals and short-circuit boolean operands
   must be skipped. Diverging function arguments, let initializers, and either
   pair component must exhaust the budget even if their values are unused.
6. All demonstrations above, nested pairs, and rejection of negative literals
   and unsupported operators even in unselected branches.
7. Structural validation that compiler output contains only the three target
   constructors and that library combinators have no free variables. Verify
   that compilation does not call the shared evaluator.

In `DESIGN.md`, state the intended correctness claim: for closed, well-typed
programs in the specified call-by-value source language that produce natural,
boolean, or finite data-pair results, observing the corresponding compiled
result yields the same data, given sufficient reduction resources. Explain
the representations and argue why translation preserves meaning for
application, conditional, let, and recursion. Discuss why delayed branches and call-by-value recursion matter
and why testing alone does not prove correctness. A full formal proof is not
required.

## Suggested milestones

1. Target AST, printer, substitution, and bounded call-by-value evaluation.
2. Church encodings with independent tests and decoders.
3. Compiler for nonrecursive programs, with scope and purity checks.
4. Recursion, complete demonstrations, documentation, and regression tests.

Keep compiler, encodings, evaluator, and demonstration code in separate modules
with clear interfaces. The evaluator must handle both source ASTs and target
terms; it must not import the compiler or invoke compilation during evaluation.
If working in a team is authorized, document contributions and how separately
developed components were integrated and reviewed.

## Submission

Submit under `MySolution/`:

- Python source for the compiler, encodings, target operations, and decoders.
- Automated tests and the executable demonstration collection.
- A slide deck presenting the project: source and target languages,
  architecture, Church encodings, call-by-value compilation (including
  delayed branches and recursion), testing, results, and limitations.
  Submit the slides as a PDF; an editable source deck may also be included.
- A **15–20 minute video recording** of a presentation based on the submitted
  slides. The presenter's face must be visible in the video, for example in
  a webcam inset alongside the slides. Explain the design
  and walk through representative compilation and execution results,
  including a recursive program. The recording must show the slides clearly
  and include audible narration. Submit a playable video file, or provide an
  accessible recording link in `README.md` if the submission system's size
  limit prevents uploading the video. Verify that the instructor can access
  the recording without requesting additional permission. Identify the slide
  and recording files or link in `README.md`.
- `README.md`: Python version, dependencies, exact setup/test/demo commands
  runnable from `assigns/06/`, module overview, budgets, and limitations.
- `DESIGN.md`: translation rules, predecessor explanation, naming policy,
  evaluation strategy, correctness argument, and design tradeoffs
  (approximately 1,000–1,500 words, excluding rules and diagrams).
- `AI-TRANSCRIPT.md`: tools used, important prompts and suggestions, and how
  you reviewed and tested the results; state explicitly if no AI was used.

Attribute reused code and external encoding references. You are responsible
for explaining and validating all submitted work. Do not submit virtual
environments, caches, or installed dependencies.

## Evaluation

| Criterion | Weight |
| --- | --- |
| Compositional compiler, complete source coverage, and pure output | 30% |
| Church encodings, arithmetic, comparisons, and recursion | 20% |
| Capture avoidance, scope, and call-by-value evaluation | 20% |
| Automated tests, decoders, and end-to-end demonstrations | 15% |
| Modular design, translation rules, and correctness explanation | 10% |
| Reproducible setup, documentation, and attribution | 5% |

Returning precomputed answers, retaining source primitives in generated code,
or using Python arithmetic inside the target evaluator does not satisfy the
central compilation requirement. Optional extensions cannot replace required
functionality.

## Optional extensions

After completing the core, consider signed integers, lists, a source
parser, or a more efficient reducer.  Explain any extension's
semantics and test it separately; do not silently change the required
language.
