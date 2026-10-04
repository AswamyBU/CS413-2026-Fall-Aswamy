# AI Transcript

## Tool

Claude Code (Anthropic's CLI assistant), model Claude Opus 5.5, plus its
Claude in Chrome browser extension for the browser smoke test.

## Prompts

1. > Can you look at Assign04.md as well as README.00 to work on this assignment, please create the ARCHITECHTURE.md, TESTING.md, and README.md file. Please do not add a reflection in the README.md
   Claude read the assignment and the stakeholder brief. It noticed that
   `lambda1.py` was not in my local `assigns/04/`, so it copied it from the
   course's upstream repository (`assigns/04/lambda1.py`). The upstream repo
   also contains an instructor solution (`public/Solution04/`). Claude
   deliberately did not open it, and none of this work is based on it.

   Claude then wrote the application, tests, and documentation (listed
   below), ran the tests, and ran a browser smoke test in Chrome.

2. > Please commit all the necessary MySolution files aside from the md files so I can check them out. Also please draft the AI Transcript and add what you worked on.

   Claude made four commits on a new `assign04` branch (backend, model and
   controller, view, then examples and tests) and drafted this file.


## What the AI produced and suggested

- **MVC structure.** The model (`model.py`) is plain Python with no Flask or
  interpreter imports and owns every state rule. The controller
  (`controller.py`) coordinates the model and the backend. The view
  (`static/view.js`) only renders snapshots. The backend sits behind a
  `LanguageBackend` protocol (`contract.py`). Claude chose to have the
  *controller* call the backend so that the model stays a pure state
  machine.
- **Restricted reader** (`reader.py`). It parses the input with `ast` and
  checks each constructor call against a schema, instead of calling `eval`
  with limited globals. This makes running uploaded code impossible by
  construction.
- **Bounded interpretation.** Interpret runs in a spawned child process with
  a 5-second timeout so a non-terminating program can be killed. Lint stays
  in-process because it is linear and bounded by the 64 KiB size limit.
- **Separate statuses** for success, input error, language error, backend
  failure, not implemented, and unavailable, so a placeholder or timeout can
  never look like a success.
- **Tests that check the architecture itself,** e.g. asserting that
  `model.py` imports only `contract.py` and that `view.js` never uses
  `innerHTML`.

## Problems found and fixed along the way

These were real problems found by running the code, not hypothetical ones:

- The first interpreter run timed out on *every* program. Part of the cause
  was the test harness (running a `spawn` child from stdin). The real bug
  was that the parent only waited on the pipe, so a crashed child looked
  like a 5-second timeout. Claude changed it to wait on the child's exit too.
- Windows rejected the 256 MB thread stack for the child, so Claude reduced
  it to 64 MB.
- The reader rejected indented input (pasted, indented code failed with
  "unexpected indent"). It now wraps the source in parentheses before
  parsing and corrects the reported line numbers.
- The "non-terminating" example actually ended with a recursion-depth error,
  because the supplied evaluator is not tail-recursive. To show the real
  timeout, Claude added a slow `fib(40)` example.
- A race in the view could overwrite newer typing with an older server
  response. Claude added an edit sequence counter.
- **Browser test failure:** during keyboard-only testing, focus jumped to the
  page body after every action. That happened because buttons are disabled
  while busy and were rebuilt on each render. Claude made the buttons
  persistent and restored focus. The re-test passed.
- Network-error messages in the status line were immediately overwritten by
  "Ready." They are now kept until the next successful request.

## Caveats

- Some browser smoke-test button presses were scripted DOM clicks rather
  than physical clicks. `TESTING.md` says this. Typing, keyboard navigation,
  menu selection, and file upload went through the real browser input paths.

## How I reviewed and tested it

I didn't rely only on Claude's test runs. I ran tests on my own machine
from Claude's quick-test checklist: the automated pytest suite and hands-on
checks of the running app in the browser. I compared what I saw against the
expected results in the checklist and the README demonstration.
