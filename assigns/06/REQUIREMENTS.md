# CS413 Midterm 1 Project: Requirements Specification

Version 1.1 — October 7, 2026

## 1. Purpose and authority

This document specifies the software and submission requirements for
[Midterm 1 (Assignment 6): Compiling Extended LAMBDA into Church's Pure Lambda-Calculus](Assign06.md).
It organizes the assignment into verifiable requirements for students,
reviewers, and graders. The assignment remains authoritative for grading and
course arrangements. Numbered requirements below restate or clarify assignment
obligations; Section 7 gives verification examples and does not create
additional grading obligations. Optional extensions are listed separately.

The system translates extended LAMBDA source ASTs into pure lambda terms,
reduces generated terms, and decodes observable data results. Compilation
must preserve program meaning under the source semantics specified here.
It must not compute source answers and then encode those answers.

## 2. Stakeholders and system boundary

| Stakeholder | Need |
| --- | --- |
| Student developer | Precise language semantics, interfaces, and testable completion criteria |
| Instructor or grader | Inspectable generated terms, reproducible demonstrations, and evidence of correctness |
| Library user or demonstration runner | Compile source ASTs, control reduction budgets, and distinguish results from failures |

The required system includes a compiler, Church-encoding library, target AST
operations, a shared evaluator with bounded target execution, decoders,
automated tests, and a command-line demonstration. Source-side evaluation is
required for terminating examples and need not be step-bounded. Required
presentation deliverables are a slide deck and a
recorded presentation based on that deck. Source programs may be constructed
directly in Python.

A source parser, static type checker, web interface, Assignment 4 integration,
signed integers, lists, and division are outside
the required scope. No external service or deployment is required.

## 3. Language contract

### 3.1 Source syntax and operations

Use the existing classes in [lambda1_vp.py](../05/lambda1_vp.py).

| Constructor | Meaning or restriction |
| --- | --- |
| `D0Eint(n)` | Natural-number literal, `n >= 0` |
| `D0Ebtf(b)` | Boolean literal |
| `D0Evar(x)` | Variable reference |
| `D0Elam(x, body)` | Single-parameter function |
| `D0Eapp(fn, arg)` | Function application |
| `D0Eop1("not", e)` | Boolean negation |
| `D0Eop2(op, left, right)` | Binary operation from the table below |
| `D0Eif0(c, t, f)` | Boolean conditional; true selects `t` |
| `D0Elet(x, init, body)` | Nonrecursive binding |
| `D0Epair(left, right)` | Ordered pair |
| `D0Epfst(e)` | First projection |
| `D0Epsnd(e)` | Second projection |
| `D0Efix(f, x, body)` | Recursive function |

| Operators | Operand kinds | Result kind | Semantics |
| --- | --- | --- | --- |
| `+`, `*` | Natural, natural | Natural | Addition, multiplication |
| `-` | Natural, natural | Natural | Truncated subtraction: `max(left - right, 0)` |
| `<`, `<=`, `>`, `>=`, `==`, `!=` | Natural, natural | Boolean | Numeric comparison |
| `and`, `or` | Boolean, boolean | Boolean | Left-to-right short-circuit conjunction or disjunction |
| `not` | Boolean | Boolean | Negation |

Boolean conjunction and disjunction are required source constructs:
`D0Eop2("and", e1, e2)` and `D0Eop2("or", e1, e2)`, respectively.
Conjunction evaluates the right operand only when the left is true;
disjunction evaluates the right operand only when the left is false.
These requirements are covered by CMP-01, CMP-08, and ENC-03.

Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Inputs may be assumed to have
valid constructor argument shapes and well-typed uses of supported operations.
This assumption does not excuse accepting negative literals or unsupported
operator spellings. Type-error detection and preservation are not required.

### 3.2 Binding and evaluation

A lambda binds its parameter in its body. A let binds its name in its body
but not in its initializer. A fix binds its function name and parameter in
its body; if they coincide, the parameter shadows the function name.

Source and target evaluation use left-to-right call-by-value. Evaluate a
function before its argument, and its argument before substitution. Evaluate
let initializers before bodies and both pair components left to right before
pair construction. Arithmetic and comparison operands are evaluated left to right.

A conditional evaluates only its selected branch; `false and e` and `true or e`
skip `e`. Compilation must implement these exceptions using lambda thunks and
force only the selected thunk. Target application remains call-by-value.
Use the single shared evaluator required by Assign06 for both source ASTs and
target terms. Its source path implements the source rules in this section; its
target path evaluates only target terms and performs no source operations.
An existing interpreter may be used as a comparison oracle only where its
operators and numeric conventions agree with this language; it does not
replace the shared evaluator or the required source-side evaluation.

### 3.3 Target syntax and representation

```text
Term ::= Var(name) | Lam(name, Term) | App(Term, Term)

TRUE   = lam t. lam f. t
FALSE  = lam t. lam f. f
NUM(n) = lam s. lam z. s applied n times to z
PAIR   = lam a. lam b. lam p. p a b
Z      = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
```

Applications associate to the left in this explanatory notation. Each target
abstraction has one parameter. Encoding names are abbreviations, not target
primitives. `NUM(0)` and `FALSE` are alpha-equivalent; decoding therefore
requires an expected result kind.

## 4. Functional requirements

### 4.1 Compilation

| ID | Requirement |
| --- | --- |
| CMP-01 | The compiler shall accept every source constructor and operator specified in Section 3.1 and return a target AST. |
| CMP-02 | The compiler shall translate compositionally, combining translations of source subexpressions. It shall not invoke the shared evaluator during compilation. A diverging source program shall still compile. |
| CMP-03 | Every generated node shall be `Var`, `Lam`, or `App`. All encoding abbreviations shall be expanded into pure terms; output shall contain no source primitives or unresolved library names. |
| CMP-04 | The compiler shall preserve lexical scope, nested shadowing, let-initializer scope, and both fix binders, including coincident binders. |
| CMP-05 | The compiler shall accept open and closed expressions and preserve `FV(C[e]) = FV(e)`. Introduced binders shall not capture source variables. |
| CMP-06 | Introduced names shall follow a documented deterministic freshness policy. Valid source identifiers such as `s`, `z`, `t`, `f`, and `x` shall remain available to source programs. Compilation shall not mutate the source AST. |
| CMP-07 | Compilation shall reject negative literals and unsupported operators throughout the source AST, including unselected branches and unapplied function bodies, with a diagnostic identifying the unsupported literal or operator. |
| CMP-08 | Translation shall implement the call-by-value source semantics in Section 3.2 and the translation rules below. |

Required translation rules, with `C[e]` denoting compilation:

```text
C[x]                 = x
C[lam x. e]          = lam x. C[e]
C[e1 e2]             = C[e1] C[e2]
C[let x = e1 in e2]  = (lam x. C[e2]) C[e1]
C[if c then t else f]= (C[c] (lam u. C[t]) (lam v. C[f])) I
C[fix f(x). e]       = Z (lam f. lam x. C[e])
```

Here `I = lam w. w` is a closed dummy value; `u` and `v` are fresh unused
parameters. Expand `I` and `Z` into pure terms. Compile `and` and `or` through
the same delayed-branch mechanism. Use `Z` for call-by-value recursion;
ordinary `Y` is unsuitable because it unfolds before producing a value.

These rules are understood up to consistent renaming of bound variables.
Students must document the remaining constructor and operator rules.

### 4.2 Church encodings

| ID | Requirement |
| --- | --- |
| ENC-01 | The encoding library shall construct the numeral, boolean, pair, and fixed-point representations in Section 3.3 as target ASTs. Every library combinator shall be closed. |
| ENC-02 | The library shall provide successor, predecessor, zero test, addition, truncated subtraction, and multiplication. Predecessor of zero shall yield zero. |
| ENC-03 | The library shall provide every required comparison, boolean operation, and pair projection, with the meanings in Section 3. |
| ENC-04 | Generated-program arithmetic shall execute through beta reduction. Python arithmetic may build literal numerals and inspect decoded answers in tests, but shall not replace operations within generated programs. |

### 4.3 Target operations and reduction

| ID | Requirement |
| --- | --- |
| TGT-01 | The target representation shall have exactly the three forms in Section 3.3, separate from the source AST. |
| TGT-02 | The target printer shall render a variable as `x`, an abstraction as `(lam x. body)`, and an application as `(fn arg)`, recursively using the same formats. |
| TGT-03 | Target operations shall compute free variables and perform capture-avoiding substitution, respecting shadowing and preserving input terms. |
| RED-01 | The evaluator shall contract `(lam x. body) v` to `body[x := v]` by capture-avoiding substitution only when `v` is a value. Target values are lambda abstractions. |
| RED-02 | Evaluation shall be weak, left-to-right call-by-value: evaluate an application’s function, then its argument, then perform substitution. It shall not reduce beneath lambdas or perform eta reduction. Execution may be restricted to closed terms with documented rejection of open inputs. |
| RED-03 | Evaluation shall accept a configurable nonnegative maximum number of beta-value steps, perform no more than that number, and report the count. Alpha-renaming does not count as a beta-value step. |
| RED-04 | The result shall distinguish value completion from budget exhaustion. A value completes with zero steps. A value reached on the last permitted step counts as completed; exhaustion means another evaluation step is required with no budget remaining. |
| RED-05 | Reduction shall be deterministic, preserve its input term, and operate exclusively on target syntax. It shall not recognize Church encodings to substitute Python computations. |

### 4.4 Observation and demonstration

| ID | Requirement |
| --- | --- |
| OBS-01 | Natural and boolean observers shall use the expected result kind and bounded pure target observation contexts evaluated by the call-by-value engine. They shall accept alpha-renamed encodings and computed encodings with redexes inside lambda bodies, inspect final observation shapes, reject malformed outputs, and report observation-budget exhaustion separately. Complete recognition of invalid untyped encodings is not required. |
| OBS-02 | Pair observation shall evaluate the pair to a value, apply Church projections, and evaluate the projected terms under step budgets before recursively observing components with their expected kinds. |
| OBS-03 | The pipeline shall evaluate recursive functions only to lambda values before applying them, without reducing under their binders. Execution and observation budgets and step counts shall be documented separately. |
| DEM-01 | One documented command shall run all mandatory examples in Section 7 through compilation, reduction, and observation. Examples may be Python-constructed source ASTs. |
| DEM-02 | Each demonstration shall show source, generated pure term or its saved-file location, reduction status, step count, expected answer, and decoded answer when available. Budget exhaustion shall be reported without claiming proven nontermination. |

## 5. Interfaces and outcomes

The following signatures describe logical contracts. Concrete function names,
classes, exception types, and packaging may differ if documented.

| Operation | Input | Successful output | Other outcome |
| --- | --- | --- | --- |
| Compile | Source AST | Pure target AST, including for open expressions | Compilation error for an unsupported literal or operator |
| Print | Target AST | String in the specified target notation | Invalid AST handling is outside scope |
| Free variables | Target AST | Set of free variable names | Invalid AST handling is outside scope |
| Substitute | Target AST, variable name, replacement target AST | Target AST with capture-avoiding substitution | Invalid AST handling is outside scope |
| Evaluate | Source AST or target term; for bounded target execution, a nonnegative beta-value-step budget | Source-language result/error or target lambda value, completion status, and step count as applicable | Target budget-exhausted status and step count; documented source errors |
| Observe natural | Target value, observation budget | Python nonnegative integer and observation step count | Malformed output or budget exhaustion |
| Observe boolean | Target value, observation budget | Python boolean and observation step count | Malformed output or budget exhaustion |
| Observe pair | Target term, expected component kinds, reduction budgets | Decoded components | Budget exhaustion or invalid-representation diagnostic |

For example, a natural observer may evaluate `n STEP BASE`, where
`STEP = lam tail. lam c. lam z. c tail` and `BASE = lam c. lam z. z`,
then count the resulting finite spine structurally, respecting alpha-renaming.
A boolean observer may apply the value to two distinct closed marker values
and identify the selected marker. These observation terms use only pure target
syntax. The host may inspect final shapes, but must not replace encoded
arithmetic with host computation or use reduction under lambdas to decode.

These contracts do not require a parser, universal type inference, or equality
checking between arbitrary functions. Decoders must not guess a result kind
or present an incomplete reduction as a successfully decoded program result.
The README must explain how statuses and diagnostics are represented.

## 6. Design, quality, and submission requirements

| ID | Requirement |
| --- | --- |
| QLT-01 | Implementation shall use Python 3.12 or later and the supplied source AST and `D0ExpVisitor` interface. Compilation shall dispatch through the visitor interface. The supplied file shall remain unchanged. |
| QLT-02 | Compiler, encodings, shared evaluator, and demonstration code shall reside in separate modules with documented interfaces. The shared evaluator accepts both source ASTs and target terms. Its target-reduction path shall operate only on target syntax and shall not import or invoke the compiler. |
| QLT-03 | The submission shall include an automated `unittest` or `pytest` suite with explicit expected outcomes and coverage of the testing obligations in Assign06; Section 7 provides representative cases. |
| QLT-04 | The submission shall include reproducible setup, test, and demonstration commands runnable from `assigns/06/`, with dependencies, Python version, chosen budgets, and limitations documented. No universal runtime threshold or exact demonstration step count is required. |
| DOC-01 | `DESIGN.md` shall document every translation rule, the predecessor construction, freshness policy, evaluation strategy, interfaces, and design tradeoffs. Target length is approximately 1,000–1,500 words excluding rules and diagrams. |
| DOC-02 | `DESIGN.md` shall state the correctness claim for closed, well-typed programs producing natural, boolean, or finite data-pair results and explain preservation of meaning for application, conditional, let, and recursion. It shall explain the need for delayed branches and call-by-value recursion and the limits of testing as proof. A full formal proof is not required. |
| DOC-03 | `README.md` shall provide the information in QLT-04 and a module overview. `AI-TRANSCRIPT.md` shall record tools, important prompts and suggestions, and review/testing of AI output, or explicitly state that AI was not used. |
| SUB-01 | Source, tests, executable examples, required documents, slides, and the recording (or its link in `README.md`) shall be submitted under `assigns/06/MySolution/`, excluding installed dependencies, virtual environments, and caches. |
| SUB-02 | Reused code and external encoding references shall be attributed. If team submission is authorized, contributions, integration, and review shall be documented. |
| DOC-04 | The student shall prepare and submit a PDF slide deck covering the source and target languages, architecture, Church encodings, call-by-value compilation including delayed branches and recursion, testing, results, and limitations. An editable source deck may also be submitted. |
| DOC-05 | The student shall submit a video recording lasting between 15 and 20 minutes, inclusive, based on the submitted slides. The presenter's face shall be visible in the video, for example in a webcam inset alongside the slides. The slides shall be clearly visible and the narration audible. The presentation shall explain the design and walk through representative compilation and execution results, including a recursive program. Submit a playable video file, or an accessible recording link in `README.md` if upload size limits prevent video submission. The student shall verify instructor access without additional permission requests and identify the slides and recording in `README.md`. |

## 7. Acceptance criteria and verification

The cases below provide concrete verification examples for requirements already
stated in Assign06 and Sections 3–6; they do not add grading requirements beyond
those sources. An implementation may use equivalent tests and examples that
demonstrate the same obligations. The cases are not a claim that an
implementation has already passed. Explanatory source notation may be replaced
with equivalent constructor-built ASTs. Define `LOOP` as
`(fix loop(x). loop x) 0`. Use documented budgets large enough for each
terminating case.

### 7.1 Mandatory end-to-end demonstrations

| ID | Source program | Expected observation |
| --- | --- | --- |
| DEMO-01 | `2 + 3 * 4` | Natural `14` |
| DEMO-02 | `2 - 5` | Natural `0` |
| DEMO-03 | `if 2 <= 3 then 7 else 9` | Natural `7` |
| DEMO-04 | `let x = 3 in (lam y. x + y) 4` | Natural `7` |
| DEMO-05 | `fst (pair 2 true)` | Natural `2` |
| DEMO-06 | `snd (pair 2 true)` | Boolean `true` |
| DEMO-07 | `(lam f. f 3) (lam x. x + 1)` | Natural `4` |
| DEMO-08 | `if true then 1 else LOOP` | Natural `1` |
| DEMO-09 | `(lam x. 0) LOOP` | Budget exhaustion |
| DEMO-10 | Recursive factorial of `4`, with `fact(0)=1` | Natural `24` |
| DEMO-11 | Recursive Fibonacci of `5`, with `fib(0)=0`, `fib(1)=1` | Natural `5` |
| DEMO-12 | `LOOP` | Budget exhaustion |
| DEMO-13 | `true and false` | Boolean `false` |
| DEMO-14 | `false or true` | Boolean `true` |

All cases verify DEM-01 and DEM-02 along with the relevant compiler,
encoding, shared-evaluator, and observation requirements.

### 7.2 Additional automated checks and reviews

| ID | Check | Expected evidence | Requirements |
| --- | --- | --- | --- |
| ACC-01 | Substitute `x := y` in `lam y. x` directly. | Result alpha-equivalent to `lam fresh. y`; `y` remains free. Test capture avoidance independently of closed-term execution. | TGT-03, RED-01 |
| ACC-02 | Evaluate `lam x. ((lam y. y) x)`; trace `(I I) (I I)` where `I = lam x. x`. | The lambda completes unchanged in zero steps. The application evaluates its left child, then its right child, then contracts the outer application. | RED-02 |
| ACC-03 | Evaluate `I` with budget zero, `I I` with budget zero, and `I I` with budget one. | Completion with zero steps; exhaustion with zero steps; completion with one step, respectively. | RED-03, RED-04 |
| ACC-04 | Repeat reduction on the same input and budget; compare input snapshots. | Same outcome and step count; input unchanged. | RED-05 |
| ACC-05 | Test every encoding independently, including predecessor of zero, equal and unequal operands, both comparison outcomes, and complete boolean truth tables. | Explicit expected natural or boolean answers; all combinators closed. | ENC-01–ENC-03 |
| ACC-06 | Compile `let x = x in x`, nested shadowing, and expressions with free `s`, `z`, `t`, `f`, and `x`. | Scope preserved; output free-variable set equals input free-variable set; repeated calls follow the documented naming policy. | CMP-04–CMP-06 |
| ACC-07 | Compile and execute recursive examples and `(fix f(f). f) 3`. | Recursive examples agree with the table; coincident-binder example returns `3`. Include capture hazards for each distinct fix binder. | CMP-04, CMP-08, OBS-03 |
| ACC-08 | Execute `let x = LOOP in 2`, `fst (pair 2 LOOP)`, `snd (pair LOOP true)`, `false and LOOP`, and `true or LOOP`. | First three exhaust their budgets; last two yield `false` and `true`. Also test divergence in either pair component and selected conditional branches. | CMP-08, ENC-03, OBS-02 |
| ACC-09 | Compile a negative literal, division, an unsupported unary operator, and unsupported forms inside an unselected branch or unapplied lambda. | Compilation errors identify the unsupported input. | CMP-07 |
| ACC-10 | Replace evaluator entry points with test doubles that fail if invoked, then compile arithmetic and `LOOP`; inspect output and source snapshots. | Compilation succeeds without evaluator calls, output uses only pure target forms, and source is unchanged. Review translation code for compositionality. | CMP-01–CMP-03, CMP-06 |
| ACC-11 | Observe alpha-renamed literals and computed arithmetic/boolean values; test malformed observation outputs and exhausted observation budgets; observe Church zero under both applicable kinds. | Computed values decode without reduction under lambdas; malformed outputs and exhaustion are distinguished; Church zero yields natural `0` or boolean `false` according to the requested kind. | OBS-01 |
| ACC-12 | Observe `pair (pair 2 true) 3` using the expected nested component kinds. | Nested result `((2, true), 3)` obtained through projections and bounded call-by-value evaluation. | OBS-02 |
| ACC-13 | Print a variable, abstraction, application, and nested target term. | Strings follow the exact recursive formats in TGT-02. | TGT-01, TGT-02 |
| ACC-14 | Review module imports, shared source/target dispatch, arithmetic implementation, and documents; run documented commands from the assignment directory. | Visitor use, target reduction confined to target syntax, no host arithmetic shortcut, successful commands, and complete deliverables. | ENC-04, RED-05, QLT-01–QLT-04, DOC-01–DOC-03, SUB-01–SUB-02 |
| ACC-15 | Open the submitted PDF slides, play the video using the submitted file or link, and check its duration. | Slides cover DOC-04 topics; the video lasts 15–20 minutes inclusive, shows the presenter's face and readable slides, includes audible narration, explains the design, and presents execution results including recursion. File locations or links are documented, and instructor access requires no additional permission request. | DOC-04, DOC-05, SUB-01 |

The automated suite must cover the obligations listed in Assign06's Testing
and correctness argument. Cases in this section are suggested concrete
coverage; details that go beyond those obligations (such as a particular
reduction trace or a particular coincident-binder execution example) are
illustrative and are not separate acceptance conditions. The suite should
cover substitution shadowing, preservation of
replacement terms, every source constructor, nested lets and lambdas, both
boolean literals, zero, and the required demonstrations. A coverage checklist
should map test cases to these obligations; test counts alone do not establish
coverage. Exact bound names need not match examples when alpha-equivalent
results are allowed.

## 8. Traceability to the assignment

| Requirements | Assignment source |
| --- | --- |
| CMP-01, CMP-04, CMP-07, CMP-08 | Starting point and scope: source language and evaluation strategy; Task 3 |
| CMP-02, CMP-03, CMP-05, CMP-06 | Objective; Task 3: Implement the compiler |
| ENC-01–ENC-04 | Task 2: Build a Church-encoding library |
| TGT-01–TGT-03, RED-01–RED-05 | Task 1: Represent and reduce pure lambda terms; Testing and correctness argument |
| OBS-01–OBS-03, DEM-01, DEM-02 | Task 4: Decode results and demonstrate the pipeline |
| QLT-01 | Starting point and scope |
| QLT-02 | Suggested milestones: module boundaries |
| QLT-03 | Testing and correctness argument |
| QLT-04, DOC-01–DOC-05, SUB-01, SUB-02 | Submission; Testing and correctness argument; Suggested milestones |

Budget-boundary cases in RED-03 and RED-04 make the assignment's maximum-step
contract explicit. Section 5 gives conceptual interfaces, not additional
prescribed Python names or return classes. The examples in ACC-01–ACC-15
instantiate the assignment's existing verification obligations.

## 9. Open arrangements and optional extensions

**Midterm 1 is due Sunday, October 25, 2026.** This deadline applies to all
required deliverables, including the slides and video presentation.

The instructor has not yet specified individual versus team submission or
the demonstration schedule. These remain unresolved course arrangements;
they do not block implementation of the specified software.

Optional extensions include signed integers, lists, parsing, Assignment 4
integration and evaluation-efficiency improvements. Document and test extension semantics separately. Extensions
must not alter the required language or replace required functionality.

Grading weights remain those in [Assign06.md](Assign06.md): compiler 30%,
encodings 20%, scope and reduction 20%, tests and demonstrations 15%, design
and correctness explanation 10%, and documentation and attribution 5%.
