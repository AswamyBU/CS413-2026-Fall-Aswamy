# Assignment 4: MVC web front end for LAMBDA

A small local web app for LAMBDA. You load or type a `d0exp` constructor
expression, and the page can lint it (check for undeclared variables),
interpret it with `d0exp_evaluate` from `lambda1.py`, and show the result as
text. Type-check and Compile are placeholders, and Execute stays disabled
because there is no compiler yet to produce code for it.

The design is described in `ARCHITECTURE.md` and the test results are in
`TESTING.md`.

## Versions

I developed and tested with Python 3.14.0 on Windows 11, in Chrome. Any Python
3.12+ should work. The only packages are Flask 3.1.3 and pytest 9.1.1 (both
pinned in `requirements.txt`).

## Commands

```
# from assigns/04/MySolution

# setup (Windows PowerShell)
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# setup (macOS / Linux)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python app.py            # start the server, then open http://127.0.0.1:5000/
python -m pytest -q      # run the tests (97 tests, about 5 s, no browser needed)
```

The server only listens on 127.0.0.1. Ctrl+C stops it.

## Files

| File | Contents |
| --- | --- |
| `model.py` | The model: applied source and its revision, the editor draft, results, the busy flag, and all the rules about what is allowed when. |
| `controller.py` | The controller: takes what the user did, checks it with the model, and calls the backend. |
| `app.py` | Flask routes. Each one just calls a controller method and returns the model's state as JSON. |
| `static/` | The view: `index.html`, `view.js`, `style.css`. It draws whatever state the server sends back. |
| `contract.py` | The result types shared by the model, controller and backend. |
| `backend.py` | Lint, Interpret, the placeholders, and the timeout. |
| `reader.py` | Turns the source text into a `d0exp` without running it. |
| `lambda1.py` | The supplied interpreter, unchanged. |
| `examples/` | Sample inputs (listed below). |
| `tests/` | The pytest tests. |

## Input format

Input is one constructor expression, for example:

```python
# comments are fine
D0Eop2("+",
       D0Eint(20),
       D0Eint(22))
```

You can use all the `d0exp` constructors from `lambda1.py` without importing
anything: `D0Eint`, `D0Ebtf`, `D0Eop1`, `D0Eop2`, `D0Evar`, `D0Elam`,
`D0Efix`, `D0Eapp`, `D0Eif0`, `D0Elet`, `D0Epair`, `D0Epfst`, `D0Epsnd`.
Arguments can be positional or keywords (`D0Evar(arg1="x")`), and literals can
be ints (including negative), `True`/`False`, or strings. The unary operators
are `+1` and `-1`. The binary ones are `+ - * / < > <= >= == !=`.

The source is parsed with Python's `ast` module and checked node by node. It
is never passed to `eval` or `exec`, so anything that isn't a constructor call
is rejected as an input error. That includes `__import__(...)`, unknown names,
wrong argument types or counts, and nesting deeper than 200 levels.

The size limit is 64 KiB. Empty or whitespace-only source is rejected, and so
are uploads that aren't valid UTF-8. When something is rejected, the
previously applied source stays in place.

## Execution limits

Interpret runs in a separate process with a 5 second timeout. If time runs
out, the process is killed, the result says "Interpretation timed out", and
the page is usable again with the source still there. Inside that process I
raised the recursion limit to 20,000 so normal recursive programs work. A
program that recurses forever usually hits that limit before the timeout and
reports "recursion too deep".

Lint runs directly in the server, since it is a single pass over the input
and the input size is already limited. Only one action can run at a time.
While one is running, the page says "Busy: running ..." and disables
everything else.

## Demonstration

Start the server and open http://127.0.0.1:5000/.

1. Factorial: pick *Factorial (canned)* in the Load source menu, press Load,
   then Interpret. It shows `Interpret · revision 1 · Success: Evaluated` and
   `D0Vint(arg1=3628800)`.

2. Fibonacci: same thing with *Fibonacci (canned)*. It gives
   `D0Vint(arg1=610)` at revision 2.

3. Undeclared variable: pick *Manual input*, press Load, and type
   `D0Evar("x")`. The action buttons stay disabled until you press Apply
   changes. Then Lint shows:
   ```
   Lint · revision 3 · Error (program): Undeclared variable(s): x
   Free (undeclared) variables:
     x
   ```
   Change the text to `D0Elet("x", D0Eint(41), D0Eop1("+1", D0Evar("x")))`
   and apply it. Now Lint says "No free variables found" and Interpret gives
   `D0Vint(arg1=42)`.

4. Lint passes but Interpret fails: enter
   `D0Elet("zero", D0Eint(0), D0Eop2("/", D0Eint(1), D0Evar("zero")))`
   (or upload `examples/runtime_error.lambda`). Lint passes because every
   variable is declared. Interpret fails with "division by zero", because Lint
   never runs the program and can't see that.

5. Placeholders: Type-check says "Type checking is not yet implemented" and
   Compile says "Compilation is not yet implemented". Execute stays disabled,
   and the note under the buttons explains that it runs code produced by
   Compile, which doesn't exist yet.

## Sample inputs

| File | Lint | Interpret |
| --- | --- | --- |
| `factorial.lambda` | passes | `D0Vint(arg1=3628800)` |
| `fibonacci.lambda` | passes | `D0Vint(arg1=610)` |
| `arithmetic.lambda` | passes | `D0Vint(arg1=42)` |
| `undeclared.lambda` | error: `x, y, z` | runtime error |
| `runtime_error.lambda` | passes | division by zero |
| `type_error.lambda` | passes | TypeError (calls an int as a function) |
| `deep_recursion.lambda` | passes | recursion too deep |
| `slow_fibonacci.lambda` | passes | times out after 5 s |
| `html_like.lambda` | error, and `<b>bold</b>` shows as plain text | runtime error |
| `malformed.lambda` | input error | input error |
| `invalid_utf8.lambda` | upload rejected | upload rejected |

## Known limitations

- There's only one workbench per server, so two tabs share the same state,
  and everything resets when the server restarts. The assignment allows
  this.
- Each Interpret takes roughly 150 ms extra to start its process.
- Function values are shown in short form, like
  `D0Vlam(<closure: lam x. ...>)`, instead of printing their whole
  environment.
- The editor sends its text to the server on every keystroke. That's fine
  locally but would need to be batched over a real network.
- Type-check, Compile and Execute aren't implemented. The format for compiled
  output is defined in `ARCHITECTURE.md`, but nothing produces it yet.
- It uses Flask's development server, which is fine for local use only.

## Reflection

MVC helped most by giving the rules one home. At first it seemed easiest to
decide in JavaScript when a button should be enabled. But the rules that
matter (no actions while edits aren't applied, a new revision clears the old
results, nothing runs while something else is busy, Execute needs compiled
code for the current revision) all fit as methods on a plain Python model. So
I could test the trickiest behavior without a browser or a server, and the
view got very small: draw the state, send the click. Putting the language
tools behind one interface helped the same way. In the tests I could swap in
a fake backend that hangs, crashes, or just records calls, which made the
busy and retry behavior easy to check.

The separation was hardest where the layers meet. The editor text lives in
the browser, but whether there are unapplied edits is a model rule, so the
text has to be synced to the server. That caused ordering problems the view
had to handle. Keyboard focus was similar. The model disables buttons while
an action runs, which is correct, but that knocked focus off the button you
just pressed, so the view had to put it back. The timeout was another one.
Limiting how long a program runs is a backend job, but it changes what the
user sees, so I added a separate "backend failure" result.

The change the design makes easiest is adding a real compiler. The compiler
just has to return a result that carries the compiled code. The model already
stores it, throws it away when the source changes or a recompile fails, and
enables Execute, and the view already shows whatever buttons and results it
gets. Nothing in the front end would need to change.
