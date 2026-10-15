# Verification — September 30, 2026

`python3 -m unittest discover -s tests -v`: **8 tests passed** on Python 3.12.3. Python compilation and `node --check static/app.js` also passed.

Automated tests cover every supported expression constructor, frozenset results, duplicate occurrences, lexical scope and let initializer scope; restricted reader rejection; real arithmetic, factorial and Fibonacci with base cases; independent lint versus runtime failures; direct adapter timeout injection; model-only source revisions/rejections; fake-backend dispatch, busy state, failure recovery and retry; placeholders and unavailable Execute.

Real Chrome smoke test: **passed**. `tests/browser-smoke.mjs` uses the Chrome DevTools protocol, with Node 21.7.3's experimental WebSocket support. Start the app on 8040 and a dedicated headless Chrome instance with `--remote-debugging-port=9224 --user-data-dir=/tmp/lambda-chrome`, then run:

```sh
node --experimental-websocket tests/browser-smoke.mjs
```

The script modifies the running application's source and leaves Factorial loaded. It writes a desktop screenshot to `/tmp/lambda-workbench.png`. The desktop screenshot was visually inspected. At 390px viewport width, the document had no horizontal overflow.

| Requirement | Check and observed result |
| --- | --- |
| F1 | Browser loaded factorial/fibonacci, manual blank editor, and uploaded a UTF-8 file; expected names/results appeared. |
| F2 | Browser edits disabled tools/source selection; Apply committed and Discard restored the applied source. |
| F3 | Browser rejected whitespace and invalid UTF-8, preserving applied source and rejected editor text; model test rejected oversize input. |
| F4 | Five actions appear in required order; source actions disable without applied source or while dirty; Execute disabled. |
| F5 | Scope tests passed; browser displayed undeclared names and successful closed lint. |
| F6 | Real factorial=120, Fibonacci=55, arithmetic=42; malformed input and runtime error tests passed. |
| F7 | Browser type-check/compile returned not-implemented; Execute remained disabled. |
| F8 | Model tests verified revision increments, cleared history/artifacts, preserved state on rejection. |
| F9 | Browser rendered an HTML-like variable name literally without creating an image element; results identify revision/action/outcome. |
| F10 | Controller fake observed busy-state rejection, then injected failure and successful retry; worker timeout was injected. Browser runtime-error recovery succeeded. |

A source-menu markup error was caught by the first browser run, corrected, and the complete smoke test rerun successfully. Real wall-clock timeout killing was not separately exercised with a deliberately nonterminating program; the timeout result path is tested by injection. No public deployment or multiple-tab concurrency test is claimed.
