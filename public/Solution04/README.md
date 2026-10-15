## Browser version on the course website

Open `static/index.html` directly as a local file, through the course website, or through any static HTTP server.
The JavaScript port runs entirely in the browser: no Python server, API, or external
runtime is required. `static/runtime.js` ports the constructor reader, free-variable
analysis, and evaluator; `static/app.js` manages state and controls; a self-contained Blob worker
isolates each operation with a three-second timeout, including when opened via `file://`. `static/examples.js` bundles
the example files. State belongs to each tab and resets on reload.

This is a hand-written JavaScript port, not automatically generated compiler output.
Integers use BigInt, including Python-style floor division. Source remains restricted
Python constructor syntax (not arbitrary Python). Type checking and compilation
remain unimplemented, as in the Python solution. Browser stack/memory limits differ
from Python; there is no portable browser equivalent of the Python 256 MiB process cap.
Changes to the Python implementation or examples must also be reflected in the port.

Run the JavaScript checks with `node tests/browser-runtime.cjs`.

# LAMBDA Workbench

A local MVC website for the supplied LAMBDA interpreter. Rebuilt in `assigns/04/Solution` at the instructor's request. Python 3.12+ on Linux/macOS; tested with Python 3.12.3 and Chrome. No third-party dependencies, installation, or build step.

```sh
cd assigns/04/Solution
python3 app.py --port 8040
```

Open http://127.0.0.1:8040. The default port, if omitted, is 8000. Stop with Ctrl+C. The server binds only to loopback. Use one browser tab: server state is shared by tabs, is kept in memory, and resets on restart. Uploaded files are never modified. Keep source files on disk if you need them after a restart.

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
```

## Try it

1. Load source → Factorial (canned), then Interpret: `D0Vint(arg1=120)`.
2. Load Fibonacci (canned), then Interpret: `D0Vint(arg1=55)`. Edit its final input, Apply changes, and run again.
3. Choose Manual input, enter `D0Evar("x")`, Apply changes, and Lint. The output lists `x` as undeclared. Replace it with `D0Elam("x", D0Evar("x"))`, apply, and lint again: no free variables.
4. Load Runtime error. Lint succeeds, but Interpret reports division by zero. Closed expressions are not necessarily valid at runtime.
5. Type-check and Compile explicitly return not-implemented results. Execute remains disabled because there is no generated code.

Typing enables Apply changes and Discard changes. Until edits are resolved, tools and source replacement are disabled. Ctrl/Cmd+Enter applies edits. Results identify their operation, revision, and outcome. Every accepted replacement clears old results.

## Input and limits

Input is one Python constructor expression, with positional arguments, literal strings/integers/Booleans, nested constructors, comments, and multiline formatting. It is not a Python script: imports, attributes, arbitrary calls, comprehensions, and keyword arguments are rejected. See the constructor reference in the page and `examples/`. `D0E000` is an abstract error form and is not accepted as source. Unary integer negation is supported. Operators follow `lambda1.py`; integer division uses `/` as the operator string.

Source is limited to 65,536 UTF-8 bytes. Each backend operation runs in a subprocess with a three-second wall-clock timeout, a three-second CPU limit, and a 256 MiB address-space limit. Python recursion limits may terminate recursive programs earlier. Very large values may exceed Python's integer-to-string limit. These resource bounds are for a local educational tool, not a public service. Actual type-checking, compilation, generated-code execution, and multi-user support are not implemented.

## Reflection

MVC helped make the applied program a clear concept instead of treating the text currently visible in the editor as the entire application. The model owns source revisions, result history, busy state, and artifact invalidation. Those rules can be tested without starting a server. The controller coordinates the language adapter and guarantees that a failed backend call restores the model to an idle state. The view can therefore concentrate on showing source, pending edits, and results.

The most difficult boundary was the distinction between a browser draft and applied source. Keeping every keystroke on the server would add requests and introduce another synchronization problem. This implementation keeps drafts in the browser and commits complete expressions explicitly. That makes Apply and Discard straightforward, but means the application is intended for a single tab. A future multi-tab implementation should use expected revision numbers on updates and reject stale writes.

Another useful separation is the restricted constructor reader. It validates the input format before interpretation and never executes uploaded Python. Lint and evaluation share the reader, but lint does not evaluate the program. Running the adapter in a bounded subprocess keeps language failures separate from the web server and lets the page recover from expensive computations.

A future compiler can replace one adapter operation and return a revision-associated artifact. The model already invalidates artifacts on source changes and compilation attempts. The controller can then pass that artifact to an execution backend, while the view continues to display ordinary operation results. That extension will require explicit artifact validation and new execution tests, rather than pretending interpretation is compiled execution.
