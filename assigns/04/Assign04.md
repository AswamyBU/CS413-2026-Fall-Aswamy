# Assignment #4
Building a LAMBDA Web Front-End with Model–View–Controller

## Due date

Tuesday, October 6, 2026.

## Attention

Keep everything you submit in `assigns/04/MySolution/`. The instructor's
reference implementation is in `Solution/`.

## Objective

Apply the Model–View–Controller (MVC) architectural pattern to build a small,
working web front-end for the LAMBDA programming language system. Users should
be able to upload or enter a program, check it for undeclared variables,
interpret it, and read textual results in the browser.

The emphasis is on separating responsibilities, managing application state,
and connecting the interface to replaceable language tools. Type-checking and
compilation are placeholders for future development; implementing a type
checker or compiler is not required.

## Scope and starting point

Read [README.00](README.00), the stakeholder brief. A local, single-user
application is sufficient. User accounts, public deployment, saved test
collections, and persistence across server restarts are not required.

Use Python 3.12 or later and the supplied [lambda1.py](Solution/lambda1.py).
For now, input is a single Python constructor expression of type `d0exp`, not
a Python script or a new concrete syntax for LAMBDA. For example:

```python
D0Eop2("+", D0Eint(20), D0Eint(22))
```

Constructor names are available without imports. Accept nested constructors,
comments, and multiline expressions. Load the expression through a restricted
constructor reader that validates arguments; do not execute arbitrary uploaded
Python or shell code. You do not need to design a LAMBDA parser.

Choose a web framework you can explain and test. Your MVC responsibilities
must be identifiable in the code; using a framework or naming three directories
is not, by itself, evidence of MVC.

## Tasks

### 1. Design the MVC architecture

Identify and separate these responsibilities:

- **Model:** Own the applied source, its revision, operation results, and any
  generated-code artifact. Enforce state rules independently of browser
  elements, HTML templates, and HTTP request objects.
- **View:** Present the source menu, editor, action controls, status, and
  textual results. Forward user interactions without embedding language
  analysis or interpretation in rendering code.
- **Controller:** Handle source changes and action requests, coordinate the
  model and backend, and arrange for the view to reflect the resulting state.

Place language-tool integration behind a separate backend interface or adapter.
Either the model or the controller may coordinate calls to this interface;
choose an approach and explain it. The view must not depend on how an
interpreter or future compiler is invoked.

Create `ARCHITECTURE.md` containing:

- A component diagram showing actual modules and dependencies.
- A responsibility table mapping MVC and the backend adapter to implementation
  files, classes, or functions.
- A sequence diagram or numbered trace for **Load source → Lint → Interpret**,
  including the response to an undeclared variable.
- Two design decisions and their tradeoffs.
- An explanation of how real type-checking and compilation could replace the
  placeholders, and how generated code would reach Execute.

Aim for approximately 1–2 pages, excluding diagrams.

### 2. Implement the language-tool interface

Define operations equivalent to the following. These are conceptual signatures,
not prescribed function names or HTTP routes.

```text
lint(source)        -> result
interpret(source)   -> result
typecheck(source)   -> not-implemented result
compile(source)     -> not-implemented result
execute(artifact)   -> result, when generated code is available
```

Associate each result with its operation and source revision. Distinguish
success, invalid input or language errors, backend failures, and operations
that are not implemented. Document this contract in `ARCHITECTURE.md`.

**Lint — real free-variable checking.** Parse the input into a `d0exp` and
compute its free variables using `d0exp_fvset`, returning a Python `frozenset`
of variable names. A nonempty set means that the program contains undeclared
variables: report an error listing their names in a deterministic order. An
empty set passes Lint. Do not evaluate the expression during linting.

Respect lexical scope: a lambda binds its parameter; a recursive function
binds its own name and its parameter in its body; a nonrecursive let binds its
name only in its body, not its initializer. Traverse all expression forms,
including both branches of a conditional. An unused binding is not an error
under this assignment's lint rule.

**Interpret — real evaluation.** Parse the input and call
`d0exp_evaluate` from `lambda1.py` with the empty environment. Display the
returned value as text, such as `D0Vint(arg1=42)`, or a useful input/runtime
diagnostic. Treat an error sentinel `D0V000()` returned directly or inside a
pair as an error rather than successful output. Interpretation requires no
compilation. Lint and Interpret may be invoked independently; passing Lint
means the expression is closed, not that evaluation will succeed.

**Type-check and Compile — placeholders.** Provide the buttons and backend
entry points, but return a clear message such as “Type checking is not yet
implemented” or “Compilation is not yet implemented.” Do not report successful
analysis or manufacture a compiled artifact. No mock type-checker or compiler
fixture system is required.

**Execute — testing generated code.** Reserve this operation for executing
code produced by a compiler. While Compile is a placeholder and no generated
artifact exists, disable Execute and explain why. Do not use interpretation
as a substitute for executing generated code. Define the intended artifact
contract so this operation can be connected later. Actual generated-code
execution is not required at this stage.

If you connect a real compiler as an extension, associate its artifact with
the source revision. Execute must consume that artifact without silently
recompiling; source changes or failed recompilation must invalidate it. Describe
this extension separately from the required functionality.

### 3. Implement the web interface

| ID | Required behavior |
| --- | --- |
| F1 | Provide a Load source menu with Choose File, Manual input, Factorial (canned), and Fibonacci (canned). Choose File uploads a local UTF-8 text file; Manual input opens a blank editor; canned examples load editable constructor expressions. Display the source name and revision. |
| F2 | Allow typing initial code without an upload and editing loaded source. Provide Apply changes and Discard changes. Applied edits update the application's copy, not the original local file. Prevent tool actions and source replacement while unapplied edits are present. |
| F3 | Reject empty or whitespace-only source, invalid UTF-8 uploads, and input exceeding a documented size limit. Preserve the previously applied source after rejection and keep rejected edits available for correction. |
| F4 | Present buttons in this order: **Lint**, **Interpret**, **Type-check**, **Compile**, **Execute**. Require applied source before invoking source-processing operations. Execute remains disabled while generated code is unavailable. |
| F5 | Lint performs real free-variable checking, reporting undeclared variable names as an error or reporting that no free variables were found. |
| F6 | Interpret evaluates the applied source with `d0exp_evaluate` and displays the value or diagnostic. Distinguish input errors from runtime failures. |
| F7 | Type-check and Compile report that they are not implemented. Explain that Execute is for generated code and is unavailable until compilation is implemented and produces an artifact. |
| F8 | Every accepted upload, canned-example selection, or applied edit creates a new source revision and clears prior results and artifacts. Rejected changes preserve applied state. |
| F9 | Show textual results with their action, source revision, and outcome. Preserve line breaks and render source and output literally, without interpreting HTML-like text as markup. |
| F10 | Show a busy status during work, prevent conflicting edits/actions, and restore controls after completion or failure. Preserve source after backend errors and allow retry. |

Use labeled controls that work with a keyboard and communicate status through
text rather than color alone. Keep the page usable during interpretation. Use
a documented timeout or other bounded execution mechanism so a nonterminating
program cannot leave the application permanently busy. Bind a local server to
the loopback interface; public hosting is outside scope.

### 4. Test behavior and architectural boundaries

Write automated tests covering:

1. Free-variable analysis for every expression constructor, duplicate variable
   occurrences, nested bindings, recursive functions, and let initializer scope.
   Verify that the returned value is a `frozenset`.
2. Lint success for a closed program and an error listing names for an open
   program. Verify that Lint does not evaluate a closed program that would
   fail at runtime, such as division by zero.
3. Real interpretation of arithmetic, factorial, and Fibonacci, including their
   base cases, and reporting of malformed input and runtime failures.
4. Manual input without upload, source replacement, editing, and rejection of
   invalid changes without losing the previous applied source.
5. Correct backend dispatch; placeholder responses must not appear as successful
   type-checking or compilation, and Execute must remain unavailable.
6. Busy-state handling, a backend failure or timeout, and successful retry.

At least one model test must run without a browser or web server. At least one
controller test must substitute a test backend without changing view code.
Mocks are appropriate for testing dispatch and injecting failures; they do not
replace the required real Lint and Interpret implementations.

Perform a browser smoke test covering the source menu, manual input, editing,
all five controls (including disabled Execute), and error recovery. Check that
HTML-like source/output is displayed literally. These checks may be manual or
automated. Record steps, expected outcomes, and observed results in `TESTING.md`,
and map automated or browser checks to F1–F10.

### 5. Document and demonstrate the application

Write `README.md` with runtime versions, exact dependency-installation,
startup, and test commands, and the URL to open. Include a demonstration of:

- Loading and interpreting the factorial and Fibonacci examples.
- Entering an open expression, such as `D0Evar("x")`, and seeing Lint report
  the undeclared variable; then editing it into a closed expression that passes.
- A runtime failure after successful Lint, showing why the two actions differ.
- The Type-check/Compile placeholder messages and explanation for disabled Execute.

Document the supported constructor-input format, execution bounds, and known
limitations. Include a 200–300 word reflection on where MVC helped, where
separation was difficult, and a future change the architecture makes easier.

## Submission

Submit the following under `MySolution/`:

- Application source, language-tool adapter, and dependency declarations.
- `README.md` with setup, demonstration, limitations, and reflection.
- `ARCHITECTURE.md` with diagrams and the backend contract.
- Automated tests and `TESTING.md` with browser results and traceability.
- Sample inputs, including factorial, Fibonacci, and error examples.
- `AI-TRANSCRIPT.md`: AI tools, important prompts and suggestions, and how you
  reviewed and tested their output. If you did not use AI, state that here.

Use meaningful Git commits. Do not submit installed dependencies, virtual
environments, caches, or secrets. Verify documented setup and tests from a
clean checkout before submission.

## Evaluation

| Criterion | Weight |
| --- | --- |
| MVC separation, dependency structure, and architectural explanation | 30% |
| Source entry/editing, controls, textual output, and error handling | 25% |
| Real Lint/Interpret integration and replaceable backend contract | 20% |
| Automated tests and browser verification | 15% |
| Reproducible setup, demonstration, reflection, and AI documentation | 10% |

A polished page with all logic embedded in event handlers does not meet the
architectural objective. A simple interface with clear responsibilities,
correct behavior, and convincing tests can earn full credit.
