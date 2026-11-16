# Assignment #8

## Animated N-Queens Search with CPS and Lazy Streams

## Due date

**Due: Thursday, November 19, 2026.**

## Attention

Keep everything you submit in `assigns/08/MySolution/`.

## Objective

Build an animated N-Queens puzzle solver that exposes its search as a sequence
of events. Implement the search in LAMBDA3 using continuation-passing style
(CPS), then expose the events through a lazy stream. A small browser client
requests events one at a time and animates queen placements, rejected choices,
backtracking, and completed solutions.

The program should make the control flow visible. A viewer should be able to
see a candidate queen placed, understand why a branch is rejected, watch the
solver backtrack, and request the next solution. This extends the JSON-RPC
service from Assign07, which reserved lazy-stream delivery across RPC calls
for this assignment.

## Starting point and scope

Use **Python 3.12 or later** and the supplied LAMBDA3 implementation in
[`LAMBDA3/lambda3.py`](./LAMBDA3/lambda3.py). The libraries in
[`LAMBDA3/mylib/`](./LAMBDA3/mylib/) and examples in
[`LAMBDA3/mytest/`](./LAMBDA3/mytest/) are available. In particular,
`eight_queens.lam` searches for one solution and `eight_queens_stream.lam`
produces all solutions in a lazy stream. Treat these as references and explain
any code you reuse.

Use the Queen Puzzle animation at
[StreamDemo2/QueenPuzzle](https://xanadu-lang.github.io/contrib/githwxi/StreamDemo2/TEST/QueenPuzzle/2020-12-12/)
as inspiration for the visualization. Students can watch the demo first to
get a better understanding of the puzzle and how its search can be animated.
Your client may use plain HTML, CSS, and JavaScript. It need not reproduce
the reference page pixel for pixel.

The required board size is **8×8**. Support sizes 4 through 10 so you can run
smaller correctness cases and larger laziness stress tests. Search one row at
a time, trying columns from left to right. A board is represented by one
column number per row, with rows and columns numbered from zero. The solver
must enumerate solutions without duplicates.

Use larger boards, such as 9×9 or 10×10, to check that your implementation
truly uses lazy evaluation. Opening a stream or requesting a short prefix
should not search for every solution first. Larger boards make eager
enumeration more noticeable, but your tests should still directly verify
that unrequested stream tails remain unevaluated.

The web application is for local use and automated tests. Authentication,
persistent databases, public deployment, and general-purpose remote code
execution are outside scope. Do not accept arbitrary LAMBDA source code from
the browser. The service exposes the fixed, reviewed puzzle solver.

## Required behavior

### Search and event model

Implement a depth-first backtracking search in LAMBDA3. Use CPS to make the
search's next action explicit: the success continuation receives a solution
and a continuation for the remaining search, while the failure continuation
resumes the next candidate or enclosing branch. Explain your continuation
conventions and how they encode the search order.

Here is the intended control-flow shape. This is pseudocode, not required
LAMBDA3 syntax:

```text
search(row, board, on_solution, on_exhausted):
  if row == size:
    on_solution(board, on_exhausted)
  else:
    try_column(row, 0, board, on_solution, on_exhausted)

try_column(row, column, board, on_solution, on_exhausted):
  if column == size:
    on_exhausted()
  else emit_lazy(try(column, row, board), lambda():
    check_safe(column, 1, board,
      lambda():
        next_board = place(column, board)
        emit_lazy(place_event(column, row, next_board), lambda():
          search(row + 1, next_board, on_solution,
            lambda(): emit_lazy(backtrack(column, row, board),
                lambda(): try_column(row, column + 1, board,
                  on_solution, on_exhausted)))),
      lambda(): emit_lazy(reject(column, row, board), lambda():
        try_column(row, column + 1, board, on_solution, on_exhausted)))

check_safe(column, distance, board, on_safe, on_conflict):
  if board is empty:
    on_safe()
  else if first_column_conflicts(column, distance, board):
    on_conflict()
  else:
    check_safe(column, distance + 1, tail(board), on_safe, on_conflict)

on_solution(board, resume):
  emit_lazy(solution(board), resume)

root_exhausted():
  emit_lazy(done, lambda(): empty_stream)

initial_stream = search(0, empty_board, on_solution, root_exhausted)
```

`emit_lazy(event, tail_thunk)` means a stream cell containing `event` whose
tail thunk does not run until the consumer asks for that tail. The success
continuation receives both the completed board and the failure continuation
that can resume search after that solution. Conceptually, its type is
`(Board, unit -> Strm[Event]) -> Strm[Event]`; the exhaustion, safe, and
conflict continuations each have type `unit -> Strm[Event]`. These functions
produce the stream as the final answer type. Search does not return a plain
board or Boolean to direct-style code. The failure continuation is a
closure over the current search point: at a nested branch it records the
backtrack and tries the next column in that row; after all root columns it
emits `done`.
The safety checker is also CPS: it calls `on_safe` when the candidate passes
all checks and `on_conflict` as soon as it finds a collision. It does not
return a Boolean for the caller to inspect. Recursive search, safety checks,
success, failure, and lazy event tails all hand control to their next
continuation in tail position.
This sketch includes `done` as the final stream event. The actual program can
organize these helpers differently, but its continuations must have these
observable roles. They must build the lazy stream rather than eagerly running
the rest of the search.

Represent the search trace as a lazy stream. Constructing the stream must not
run the full search. Forcing one cell may do enough search work to produce
the next event, but must not enumerate the rest of the tree. The consumer
should be able to stop after any event or solution without forcing the tail.

The stream must contain these event kinds:

| Event | Required data | Meaning |
| --- | --- | --- |
| `try` | column, row, current partial board | Consider and display a candidate placement. |
| `place` | column, row, updated partial board | Candidate is safe and is added to the board. |
| `reject` | column, row, current partial board | Candidate conflicts with an earlier queen. |
| `backtrack` | column, row, restored partial board | A branch failed; resume at the next candidate. |
| `solution` | complete board | One valid arrangement was found. |
| `done` | none | Final event: no further solutions remain. |

The intended high-level search is “try a column in the next row; if safe,
place it and search the next row; otherwise record the rejection; when a row
has no columns left, backtrack.” Avoid emitting redundant events for
internal implementation details. Include `done` exactly once as the final
stream event.

The 8×8 run must find exactly 92 distinct boards. Each board is an
eight-element tuple listing the queen column for rows 0 through 7. The trace
may include failed branches before, between, and after solutions.

### RPC service

Implement one HTTP endpoint, `POST /rpc`, using JSON-RPC 2.0 and
`application/json`. Reuse your Assign07 service if available, or implement
the small required subset below. Keep JSON-RPC envelope handling, search
logic, and web-client code in separate modules.

| RPC method | Parameters | Result |
| --- | --- | --- |
| `service.health` | `{}` | `{ "status": "ok", "version": "1.0" }` |
| `queens.open` | `{ "size": 8 }` | `{ "stream_id": "...", "size": 8 }` |
| `queens.next` | `{ "stream_id": "...", "limit": 1 }` | `{ "events": [...], "done": false }` |
| `queens.close` | `{ "stream_id": "..." }` | `{ "closed": true }` |

`queens.open` creates a fresh search and returns without forcing the first
event. `queens.next` forces at most `limit` events, where `limit` is an integer
from 1 through 32. Return fewer events if the stream ends. The response that
includes the final `done` event sets `done` to `true`; subsequent `queens.next`
calls return an empty event list and `done: true`. Each event is a JSON object
with an `event` field and the data required by the event table. A board is
encoded as an array of column numbers in row order.

Stream IDs are unguessable within the running process (a UUID is sufficient).
An unknown, closed, or expired ID returns a documented application error.
Provide `queens.close` and remove exhausted streams so clients can release
state. Set a documented inactivity lifetime for open streams. The service
does not need durable stream storage: a server restart may invalidate IDs.

Validate request envelopes, method names, parameter object shapes, board
size, and event limits. Accept sizes 4 through 10. Preserve JSON-RPC request
IDs. Use standard codes for
invalid request (`-32600`), unknown method (`-32601`), invalid parameters
(`-32602`), and internal error (`-32603`). Define and document an application
error for unknown or expired stream IDs. Do not expose Python tracebacks,
filesystem paths, or internal continuation/closure objects in responses.

Support calls and notifications. A valid notification receives no response
body and uses HTTP 204. A successful call or JSON-RPC error response uses HTTP
200. Batch support is optional; if implemented, document how batches interact
with stream state and cover them in tests. All stream state is process-local.

### Browser animation

Build a page with an 8×8 chessboard and controls for **Start**, **Step**,
**Play/Pause**, **Next solution**, and **Reset**. Show a visible status or
event log. Animate `try`, `place`, `reject`, `backtrack`, and `solution` events
with distinct visual states. The interface must request events incrementally;
it must not fetch the full trace before playback. Let the user adjust playback
speed or step manually. Show the number of solutions found and distinguish
search completion from a solution event.

Use ordinary DOM or canvas rendering. The page should remain usable without
an external service or account. Include an error message for network or RPC
failures and a control to restart the search after completion.

## Tasks

### 1. Specify the design

Create `DESIGN.md` before implementation. Include:

- The solver state and the invariant for a partial board.
- The CPS success and failure continuation signatures, with pseudocode for
  trying a candidate and resuming search.
- How the CPS search becomes a lazy stream and what work is done when a cell
  is forced.
- The event schema and one example JSON-RPC exchange for each method.
- Stream lifetime, cleanup, limits, and error behavior.
- A diagram showing the browser, HTTP endpoint, RPC dispatcher, stream table,
  LAMBDA3 solver, and lazy stream.

### 2. Implement the solver

Implement and type-check the CPS search and lazy event stream in LAMBDA3.
Keep the solver independent of HTTP and browser concerns. Separate pure
functions for checking queen safety, extending the partial board, and
constructing events. Do not compute all solutions eagerly and then convert
the resulting list to a stream.

The CPS search must enumerate every solution in deterministic depth-first
order. The stream must preserve that order. If CPS is used only as a wrapper
around the existing direct-style solver, the CPS requirement is not met.

### 3. Implement the RPC adapter

Implement the required methods and per-stream state. One practical design is
to store the current lazy stream value under each stream ID and replace it
with its tail after each returned event. Keep the state update atomic with
respect to one request. Do not serialize interpreter environments or lazy
closures; convert each event to the documented JSON representation.

The API should expose only the fixed Queen solver. It must not evaluate source
text or accept arbitrary function names from a request. Validate all input
before allocating a stream.

### 4. Implement the browser client

Use the RPC methods above to open a stream and fetch event batches as playback
needs them. The event renderer should update the board from the event's board
snapshot or apply the event's placement/removal. Keep search, transport, and
rendering responsibilities separate enough to test.

### 5. Test and document

Use automated tests for solver, stream, HTTP, and client behavior. Tests must
verify that opening a stream does not force it and that reading a bounded
number of events does not force later events. Include an end-to-end run of the
8×8 puzzle and verify all 92 solutions and the final done state.

Write `README.md` with Python version, dependencies, setup, exact test and run
commands, local URL, controls, RPC examples, and limitations. Include a short
`TESTING.md` mapping requirements to test names and observed results. Write
`AI-TRANSCRIPT.md` listing AI tools and meaningful prompts/suggestions, plus
how you reviewed and tested the work; state explicitly if no AI was used.

## Required tests

At minimum, cover:

1. Safety checks: same row, both diagonal directions, and a safe placement.
2. CPS success and failure paths, including resumption at the next candidate.
3. All 8×8 solutions, exact solution count (92), deterministic order, and no
   duplicates.
4. Each required event kind and the correct board snapshot and coordinates.
5. Lazy construction: opening/constructing the stream performs no search;
   forcing one cell does not force its tail; taking a bounded prefix leaves
   later work unforced.
6. Stream exhaustion, repeated `next` after exhaustion, close, unknown ID,
   cleanup, and expiration behavior.
7. JSON-RPC IDs, malformed envelopes, unknown methods, invalid parameters,
   notifications, and application errors.
8. `queens.next` respects limits 1 and 32, and returns no more than the
   requested number of events.
9. HTTP client flow from open through all 92 solution events to completion.
10. Browser controls: start/reset, step, play/pause, next solution, and
    visible RPC failure handling. Use a browser automation tool or a small
    documented manual test checklist for UI behavior.

Successful solver tests must exercise the LAMBDA3 implementation. Test
doubles may be used for injected transport failures and expiration clocks.
Do not test laziness merely by inspecting a formatted `<lazy>` value; include
an observable counter, trace hook, or a delayed failing computation that
proves unrequested tails were not forced.

## Submission

Submit under `MySolution/`:

- LAMBDA3 CPS search and lazy stream implementation.
- RPC service and dependency declarations.
- Browser client source and static assets.
- Automated tests for solver, stream, service, and client behavior.
- `DESIGN.md`, `README.md`, `TESTING.md`, and `AI-TRANSCRIPT.md`.

Do not submit virtual environments, caches, installed dependencies, secrets,
or generated runtime state. Verify the documented tests and run commands from
the assignment directory.

## Evaluation

| Criterion | Weight |
| --- | --- |
| Correct CPS search and exhaustive deterministic solutions | 25% |
| Genuine lazy event stream and incremental consumption | 20% |
| RPC contract, stream lifecycle, validation, and errors | 20% |
| Clear and functional animation and controls | 20% |
| Tests, architecture, and reproducible documentation | 15% |

An eager solution list presented as a lazy stream, a direct-style search with
decorative continuation parameters, or a client that downloads the full trace
before playback does not meet the central requirements.

## Optional extensions

Pause/resume across browser reloads, or visualize search statistics such as
attempted placements and backtracks. Extensions must preserve bounded lazy
consumption and the required 8×8 behavior.
