# AI Transcript

## Tools used

* **Claude Code** (Anthropic, model Claude Opus 5.5), in the Claude desktop
  app, working directly in this repository with file, shell, and in-app
  browser access.

## Prompt

> Please complete assign08 as instructed in the Assign08.md, write what you contributed in the AI-Transcript.

>Please walk me through how this works, and provide me the commands to run some tests.

>Please run all of your tests to check.

## What the AI did

1. Read `Assign08.md`, the relevant parts of `LAMBDA3/lambda3.py` (syntax,
   value representation, `d0exp_evaluate`, `d0exp_compile`), the libraries in
   `LAMBDA3/mylib/`, the reference solvers `eight_queens.lam` and
   `eight_queens_stream.lam`, and my Assign07 JSON-RPC service.
2. Wrote the CPS solver in `queens/queens.lam`, following the assignment's
   pseudocode:
   * `try_column` contains a local `search`, because LAMBDA3 has no mutually
     recursive `let`.
   * `check_safe` is CPS (it calls `on_safe`/`on_conflict` instead of
     returning a Boolean) and is polymorphic in its answer type.
   * `emit_lazy` delays both the stream cell and its tail, so each forced
     cell runs the search only as far as the next event.
   * Only the three-way attack comparison is reused from
     `eight_queens.lam`; the rest is new.
3. Profiled the first 8×8 run, which took about 20 s in the interpreter
   (mostly `isinstance` checks). It then ran the same type-checked program
   through LAMBDA3's own `d0exp_compile` instead (about 0.14 s). The
   interpreter stays available as a backend (`--backend interpreter`), and
   tests show both produce identical traces.
4. Chose the design:
   * The HTTP server uses the Python standard library (`http.server`), so
     there are no dependencies. JSON-RPC handling (adapted from my Assign07
     `jsonrpc.py`/`errors.py`), validation, the stream table, and the solver
     bridge are separate modules.
   * A stream table with per-stream locks, a 300 s idle expiry, and a cap of
     64 open streams.
   * When `done` is sent, the solver state is freed but a small "exhausted"
     record is kept. Later `next` calls can then still return
     `{"events": [], "done": true}`.
   * Application errors -32001 (stream not found) and -32002 (too many
     streams). Batch requests are rejected with -32600.
   * The browser client is split into `rpc.js` (transport), `board.js` (pure
     event-to-view reducer), `player.js` (buffer, timer, stale-request
     guard), and `main.js` (DOM).
5. Added laziness checks that do more than look at `<lazy>` text:
   * a counter of forced delayed computations (thunks) in the compiled
     backend;
   * a call-trace hook that counts `try_column`/`check_safe` calls in the
     interpreter;
   * checks of the `evaluated` flag on unforced tails;
   * a root continuation that divides by zero, which only runs if its event
     is requested.
6. Wrote `DESIGN.md`, the implementation, the Python and Node test suites,
   `README.md`, `TESTING.md`, and this file.

## Suggestions I should review

* Running the compiled LAMBDA3 output by default instead of the interpreter.
* Keeping an "exhausted" record after `done`, rather than deleting the stream
  outright.
* No batch support, and the limit values: 300 s TTL, 64 open streams, 64 KiB
  body, and 8/32 events per client request.
* "Same row" safety is tested as "same column". Rows are implicit in this
  board layout, so two queens can never share a row.

## How the result was reviewed and tested

* Ran the Python suite (58 tests) and the Node client suite (14 tests) from
  `assigns/08` with the exact README commands; all pass. The slow full 8×8
  interpreter test also passes (about 21 s).
* Checked solution order and count against an independent brute-force oracle
  for sizes 4–8: 92 distinct solutions for 8×8, in depth-first order.
* Testing found a client bug: `player.js` dropped the stream id when the
  server reported `done`, while events were still buffered, so playback
  stopped early. It was fixed by keeping the id until Reset/Restart. Two wrong
  test expectations were also corrected, and the Node test command was changed
  to a glob, because Node 24 rejects a bare directory.
* Ran the real server and clicked through the page in a browser: Start,
  Step, Play/Pause, and Next solution through all 92 solutions to
  completion; Restart; Reset; an expired-stream error; a simulated network
  failure; a 4×4 board; and phone width. The results are recorded in
  `TESTING.md`.
