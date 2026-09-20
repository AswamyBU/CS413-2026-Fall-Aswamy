# LAMBDA Concrete Syntax: Requirements Engineering Document

Status: Draft for discussion  
Date: 2026-09-18  
Baseline: `lambda1.py` and `TEST/test03_lambda1.py` in this lecture directory

## 1. Purpose

Define requirements for a source-text notation for LAMBDA so that students can
write, read, and run programs without constructing Python AST objects manually.
The notation should make binding, scope, application, and recursion clear while
remaining small enough to explain and implement in a compiler course.

This document precedes the concrete grammar and parser implementation. Existing
interpreter behavior is the compatibility baseline. Proposed spellings below
are examples for review, not an approved language specification.

## 2. Users and use cases

| User | Need | Success criterion |
| --- | --- | --- |
| Student writing programs | Express examples without Python constructor boilerplate. | Write arithmetic, closures, pairs, and recursive functions in source text. |
| Student studying syntax | Relate source notation to abstract syntax. | Explain which AST a source expression denotes, including its binding structure. |
| Instructor | Present compact examples with predictable interpretation. | Demonstrate lexical scope, shadowing, and evaluation order without syntactic ambiguity. |
| Parser implementer | Work from precise, testable rules. | Implement tokenization and parsing without guessing precedence or delimiters. |

Representative programs include increment, a closure that captures a variable,
ordinary factorial, and tail-recursive factorial with a pair carrying the input
and accumulator.

## 3. Scope and priorities

**Must:** Cover every supported expression constructor, specify lexical and
grammatical rules, produce existing ASTs, preserve evaluation behavior, and report
invalid source with useful locations.

**Should:** Use familiar ASCII notation, allow readable multiline programs and
comments, and support a straightforward instructional parser.

**Deferred:** Multiple top-level definitions, modules, imports, static typing,
type inference, strings, lists, records, pattern matching, assignment, a REPL,
editor integration, and a formatter. Multiple parameters or arguments may be
considered later as syntactic sugar.

Tail-call optimization is outside this syntax project. A tail-recursive source
program must be expressible, but the current evaluator still uses Python
recursion.

## 4. Functional requirements

Identifiers below are stable references for design decisions and acceptance
tests. “Shall” denotes a required behavior in the proposed first version.

### 4.1 Source input and lexical structure

| ID | Requirement |
| --- | --- |
| LEX-01 | Source shall be plain text; file input shall use UTF-8. The core notation shall be writable using ASCII characters. |
| LEX-02 | The specification shall define identifier characters, case sensitivity, reserved words, and whether Unicode identifiers are accepted. Keyword prefixes inside longer identifiers shall not become separate keyword tokens. |
| LEX-03 | Decimal integer and Boolean literals shall be supported. The specification shall settle negative integer notation, leading zeros, and literal boundaries such as `123abc`. Floating-point literals are outside the first version. |
| LEX-04 | Spaces, tabs, and line endings shall separate tokens without changing expression structure. Indentation shall not determine scope. LF and CRLF source shall be supported. |
| LEX-05 | A line-comment notation shall be provided. The specification shall define its interaction with operators and end of file. Block comments are optional. |
| LEX-06 | Overlapping operator tokens, including `<`/`<=`, `>`/`>=`, and `=`/`==`, shall have a deterministic tokenization rule. Unknown characters shall cause lexical errors. |

### 4.2 Expression coverage and AST mapping

| ID | Required source capability | Existing AST target |
| --- | --- | --- |
| SYN-01 | Integer and Boolean literals | `D0Eint`, `D0Ebtf` |
| SYN-02 | Variable references | `D0Evar` |
| SYN-03 | Anonymous function with one parameter and a body | `D0Elam` |
| SYN-04 | Recursive function with an explicit self name, one parameter, and a body | `D0Efix` |
| SYN-05 | Application of any expression to one argument | `D0Eapp` |
| SYN-06 | Nonrecursive local binding with initializer and body | `D0Elet` |
| SYN-07 | Boolean conditional with condition and both branches | `D0Eif0` |
| SYN-08 | Increment and decrement | `D0Eop1` with `+1` and `-1` |
| SYN-09 | Integer arithmetic: `+`, `-`, `*`, `/` | `D0Eop2` |
| SYN-10 | Integer comparisons: `<`, `>`, `<=`, `>=`, `==`, `!=` | `D0Eop2` |
| SYN-11 | Ordered pair construction and first/second projections | `D0Epair`, `D0Epfst`, `D0Epsnd` |
| SYN-12 | Parenthesized grouping of any expression | No additional AST constructor |

Every compound expression shall admit nested expressions in its expression
positions. Application shall support anonymous functions and computed functions,
not just named variables. Pairs shall permit mixed values and nested pairs.

The parser shall construct `D0Elet` for a source let, preserving the new construct
instead of lowering it to lambda application. Any other syntactic sugar must
have an explicit, semantics-preserving AST translation.

### 4.3 Grammar and disambiguation

| ID | Requirement |
| --- | --- |
| GRM-01 | The final syntax specification shall provide a complete grammar, token definitions, and AST construction rules. |
| GRM-02 | A program shall contain exactly one expression followed by end of input, allowing surrounding whitespace and comments. Empty input and trailing noncomment tokens shall be errors. |
| GRM-03 | Every accepted expression shall have one specified parse. Precedence and associativity shall cover application, projections, unary operations, arithmetic, and comparisons. |
| GRM-04 | The grammar shall define the extent of lambda, fix, let, and conditional bodies, including nested conditionals and lets. Both conditional branches are mandatory. |
| GRM-05 | The grammar shall distinguish grouping, pair construction, and application, and specify repeated application such as applying a returned function. |
| GRM-06 | Comparison chaining shall either be rejected or given an explicit translation. It shall not acquire unintended meaning from accidental associativity. |
| GRM-07 | Negative literals, subtraction, and decrement shall have distinct, documented interpretations, including their interaction with whitespace and application. |

### 4.4 Semantic compatibility

| ID | Requirement |
| --- | --- |
| SEM-01 | Evaluating a parsed expression shall produce the same value or runtime failure as evaluating its corresponding manually constructed AST in the same environment. Parsing itself shall not evaluate the program. |
| SEM-02 | Binding shall remain lexical. A let initializer uses the outer environment; its new binding is visible only in the body. Shadowing is allowed. |
| SEM-03 | Application shall retain call-by-value semantics. Binary operands and pair components retain left-to-right evaluation; unused arguments and let initializers are still evaluated. |
| SEM-04 | Conditionals require Boolean values and evaluate only the selected branch. The source notation shall not imply an integer-zero test despite the AST name `D0Eif0`. |
| SEM-05 | Division shall retain integer floor division. Operators, projection checks, and application checks retain the evaluator's existing behavior. |
| SEM-06 | Free variables shall be syntactically legal, permitting evaluation in an explicit environment. An unresolved variable retains the evaluator's `D0V000()` sentinel behavior. |
| SEM-07 | A recursive function's self name and parameter shall retain their existing scopes. If the names coincide, the parameter shadows the self name. |

### 4.5 Parser integration and diagnostics

| ID | Requirement |
| --- | --- |
| INT-01 | A Python entry point shall accept source text and return a `d0exp` compatible with `d0exp_evaluate`. Its exact name and error API shall be specified before implementation. |
| INT-02 | Existing AST construction and evaluation APIs shall remain usable. Source parsing shall not depend on executing source as Python or calling Python `eval` or `exec`. |
| ERR-01 | Lexical and syntactic failures shall be distinguishable from runtime failures. Ill-typed but syntactically valid expressions shall reach the existing runtime checks. |
| ERR-02 | A source error shall identify a one-based line and column, the unexpected token or end of input, and a useful description of what was expected. |
| ERR-03 | Missing delimiters, missing operands, malformed bindings, and incomplete conditionals shall produce deliberate diagnostics rather than internal parser exceptions. |
| ERR-04 | The parser may stop at the first error. Error recovery and source locations on runtime failures are deferred. |

## 5. Candidate notation for discussion

The following is one coherent starting point. Spellings and delimiters remain
open decisions; this table is not a complete grammar.

| Construct | Candidate notation |
| --- | --- |
| Literals and variables | `42`, `-7`, `true`, `false`, `counter` |
| Lambda | `lam x. body` |
| Recursive function | `fix f(x). body` |
| Application | `f(argument)` |
| Let | `let x = value in body end` |
| Conditional | `if condition then yes else no end` |
| Increment/decrement | `succ(expr)`, `pred(expr)` |
| Arithmetic/comparison | `a + b`, `a <= b` |
| Pair and projections | `(a, b)`, `fst(pair)`, `snd(pair)` |

An illustrative tail-recursive factorial under this proposal is:

```text
let factorial =
  lam n.
    let loop =
      fix loop(state).
        let n = fst(state) in
          let acc = snd(state) in
            if n <= 1 then acc
            else loop((n - 1, n * acc)) end
          end
        end
    in loop((n, 1)) end
in factorial(5) end
```

This example should evaluate to `D0Vint(120)`. It exercises recursion,
application, pairs, projections, local bindings, arithmetic, and a conditional.
The recursive call is in tail position because its result is returned directly.

## 6. Decisions to resolve during syntax design

| ID | Decision | Proposed starting point / tradeoff |
| --- | --- | --- |
| DEC-01 | Application notation | Use `f(x)` for familiarity and clear argument boundaries; juxtaposition `f x` is closer to traditional lambda calculus. |
| DEC-02 | Scope delimiters | Use `end` for lets and conditionals; lambda and fix bodies extend as far right as the enclosing syntax permits. More delimiters improve visibility but add text. |
| DEC-03 | Unary operations | Reserve `succ` and `pred` for the existing increment/decrement operations; avoid confusion with unary signs. |
| DEC-04 | Identifiers and literals | Start with case-sensitive ASCII identifiers `[A-Za-z_][A-Za-z0-9_]*`, lowercase Boolean keywords, and decimal integers. Specify sign handling separately from digit tokenization. |
| DEC-05 | Precedence | Start with application/projection, then multiplication/division, then addition/subtraction, then nonassociative comparisons. Arithmetic is left-associative. Specify negative literals and body forms in the grammar. |
| DEC-06 | Comments | Use `#` through end of line; it avoids a conflict between division and `//` comments. |
| DEC-07 | Reserved words | Reserve the chosen binding, Boolean, conditional, and primitive-operation keywords; publish the complete list. |
| DEC-08 | Integration | Start with a text-to-AST library function; a file runner or CLI can be a separate follow-up. |

## 7. Acceptance criteria and verification

The later parser implementation shall include the following tests. These are
requirements for future work, not claims that a parser already exists.

| Test group | Acceptance criterion | Requirements covered |
| --- | --- | --- |
| Constructor coverage | At least one source example parses to the expected AST for every supported expression constructor. | SYN-01–12, INT-01 |
| Lexical boundaries | Test keyword prefixes, reserved names, integer boundaries, negative numbers, adjacent operators, comments, LF, and CRLF. | LEX-01–06, GRM-07 |
| Parse structure | Assert AST structure for mixed precedence, subtraction/division associativity, repeated application, grouping versus pairs, and nested bindings/conditionals. | GRM-01, GRM-03–07 |
| Binding and closures | Compare parsed and manual AST programs for shadowing, outer-scope initialization, captured variables, and recursive self binding. | SEM-01–02, SEM-06–07 |
| Evaluation order | Use division-by-zero and invalid operands to check eager initialization, left-to-right evaluation, and unselected conditional branches. | SEM-03–05 |
| Factorial examples | Ordinary and tail-recursive factorial return 1, 1, 120, and 5040 for inputs 0, 1, 5, and 7 respectively. | SYN-04–11, SEM-01 |
| Invalid source | Empty input, trailing tokens, unknown characters, missing delimiters, missing branches, and malformed bindings report the expected location and error category. | GRM-02, ERR-01–04 |
| Runtime separation | A valid expression applying an integer or adding a Boolean parses successfully and fails during evaluation. Free variables remain parseable. | SEM-06, ERR-01 |
| Regression | Existing interpreter tests continue to pass, including normal, `-O`, and `-OO` execution. | INT-02, SEM-01 |

## 8. Risks and completion gate

The principal design risks are ambiguous scope boundaries, confusing signed
literals with decrement, and accidentally changing semantics through syntactic
sugar. Address them with explicit grammar rules and AST-level examples before
parser coding. Keep instructional readability ahead of adding extra syntax.

Requirements review is complete when the first-version scope and decisions
DEC-01–08 are settled. The next deliverable is a concrete syntax specification
with lexical rules, EBNF, precedence, AST mappings, and valid/invalid examples.
Implementation is complete only after the acceptance criteria above pass.
