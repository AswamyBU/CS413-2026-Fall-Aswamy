# DESIGN: Animated N-Queens with CPS and Lazy Streams

## 1. Architecture

```text
 Browser (web/)                          Python process (queens/)
┌──────────────────────────────┐        ┌───────────────────────────────────────────────┐
│ main.js   DOM + buttons      │        │ server.py   HTTP: POST /rpc, GET / (static)   │
│   │ render(view)             │        │   │ raw bytes                                 │
│ player.js playback, buffer,  │ HTTP   │ jsonrpc.py  envelope, ids, codes, notif.      │
│   │       timer, generation  │ POST   │   │ params dict                               │
│ board.js  event -> view      │ /rpc   │ service.py  validation (size, limit, id)      │
│   (pure reducer)             │ ─────► │   │                                           │
│ rpc.js    JSON-RPC over fetch│ ◄───── │ streams.py  StreamTable: uuid -> entry        │
└──────────────────────────────┘ JSON   │   │  {cursor, lock, last_used, counters}      │
                                        │   │ force one cell at a time                  │
                                        │ solver.py   EventStream + backend bridge      │
                                        │   │                                           │
                                        │ queens.lam  LAMBDA3 CPS search                │
                                        │   └── lazy stream: Strm[Event]                │
                                        │       cell0 ─► cell1 ─► ... (tails suspended) │
                                        └───────────────────────────────────────────────┘
```

Each layer only knows the layer below it. `queens.lam` knows nothing about
Python; `solver.py` knows nothing about HTTP; `jsonrpc.py` knows nothing about
queens; the browser never sees LAMBDA3 values, only JSON events.

## 2. Solver state and invariant

A **partial board** is `List[sint]`, one column per placed queen, **newest row
first**: for a board of length `k`, rows `0..k-1` are filled and the queen of
row `k-1-i` is element `i`. Newest-first makes extending O(1) (`list_cons`) and
lets the safety check walk outward from the candidate (`distance = 1, 2, ...`).

**Invariant:** no two queens on a partial board attack each other (no shared
column, no shared diagonal; rows are distinct by construction). `place` is
only ever called from `on_safe`, so the invariant holds for every board the
search creates. Events carry the board **in row order** (`board_rows`
reverses it), which is what the JSON API exposes.

Search state at any moment = `(n, row, column, board, on_solution, on_exhausted)`
— the arguments of `try_column`. Nothing else is mutable.

## 3. CPS conventions

The answer type is `Strm[Event]`. Every continuation returns it:

```text
on_solution : (Board, unit -> Strm[Event]) -> Strm[Event]   -- success
on_exhausted: unit -> Strm[Event]                           -- failure
on_safe     : unit -> Strm[Event]
on_conflict : unit -> Strm[Event]
check_safe[A] : (column, distance, Board, unit -> A, unit -> A) -> A
```

- **Success** gets the complete board *and* the failure continuation that
  resumes the search after that solution. `on_solution` emits `solution`
  and hands that failure continuation to the stream as its tail.
- **Failure** (`on_exhausted`) is a closure over the current search point.
  For a nested row it is "emit `backtrack(column,row,board)` for the parent
  queen, then try the parent's next column". At the root it emits `done`.
- `check_safe` is CPS too: it calls `on_conflict()` as soon as a queen attacks
  the candidate and `on_safe()` after the last queen. It never returns a
  Boolean to inspect. (It is polymorphic so tests can instantiate it at `bool`.)
- All of these calls are in tail position.

Trying a candidate and resuming (actual structure of `try_column` in
`queens.lam`; `search` is a local helper so the two can be mutually recursive
with LAMBDA3's single-function `fix`):

```text
try_column(n, row, column, board, sk, fk):
  next_column = λ(). try_column(n, row, column+1, board, sk, fk)
  if column == n: fk()                                  -- row exhausted
  else emit_lazy(try(column,row,board), λ().
         check_safe(column, 1, board,
           λ(). let b' = place(column, board) in          -- on_safe
                emit_lazy(place(column,row,b'), λ().
                  search(row+1, b', λ().                  -- fk for the child
                    emit_lazy(backtrack(column,row,board), next_column))),
           λ(). emit_lazy(reject(column,row,board), next_column)))  -- on_conflict

search(row, board, fk) = if row == n then sk(board, fk)
                         else try_column(n, row, 0, board, sk, fk)

on_solution(board, resume) = emit_lazy(solution(board), resume)
root_exhausted()           = emit_lazy(done, λ(). empty)
queens_stream(n)           = lazy(λ(). force(try_column(n, 0, 0, [], on_solution, root_exhausted)))
```

Columns are tried left to right, rows top to bottom, and the failure
continuation always resumes at `column + 1` of the most recent choice point.
That is exactly depth-first order, so solutions come out in lexicographic
order (tests compare against a brute-force oracle).

## 4. From CPS to a lazy stream

```text
emit_lazy(ev, k) = lazy_make(λ(). stcn_cons(ev, lazy_make(λ(). lazy_eval(k()))))
```

`emit_lazy` does no work when called — it only allocates a suspension. So:

- **Constructing** `queens_stream(n)` allocates one suspension and runs no
  search code (`try_column` is not even called).
- **Forcing one cell** runs CPS code from the previous tail up to the next
  `emit_lazy` and stops. Concretely, forcing the tail after `try` runs one
  `check_safe` walk (≤ n-1 steps) and lands on `place` or `reject`; forcing
  after `reject` runs `next_column` and lands on the next `try`, or calls the
  failure continuation, which lands on `backtrack`/`done`. Every event costs
  exactly two thunk evaluations (the tail and the cell), which the tests
  measure.
- The CPS stack never grows across cells: the "rest of the search" is
  captured in the closures `k`, not in a Python or LAMBDA3 call stack.

Python (`EventStream`) keeps only the current unforced value and replaces it
with the tail after each event, so already-delivered cells become garbage.

**Backends.** `solver.py` parses and type-checks `queens.lam` once, then runs
that AST either with LAMBDA3's own compiler (`lambda3.d0exp_compile`, default;
about 0.15 s for the whole 8×8 trace) or with the reference interpreter
(`lambda3.d0exp_evaluate`, about 20 s). Both produce identical traces (tested).
No search logic is written in Python.

## 5. Events

| `event` | fields | meaning |
| --- | --- | --- |
| `try` | `column`, `row`, `board` (current) | candidate considered |
| `place` | `column`, `row`, `board` (with new queen) | candidate safe, placed |
| `reject` | `column`, `row`, `board` (current) | candidate attacked |
| `backtrack` | `column`, `row`, `board` (restored, queen removed) | branch exhausted; next column follows |
| `solution` | `board` (complete), `number` | one arrangement |
| `done` | — | final event, exactly once |

Every event also has `seq` (0-based position in the stream), added by the
stream table. In LAMBDA3 an event is the tuple
`(kind, column, row, board)` with kinds `0..5`; `solution`/`done` use `-1` for
column/row (dropped in JSON).

## 6. RPC examples

```json
→ {"jsonrpc":"2.0","method":"service.health","params":{},"id":1}
← {"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":1}

→ {"jsonrpc":"2.0","method":"queens.open","params":{"size":8},"id":2}
← {"jsonrpc":"2.0","result":{"stream_id":"6f1c…-uuid","size":8},"id":2}

→ {"jsonrpc":"2.0","method":"queens.next","params":{"stream_id":"6f1c…","limit":3},"id":3}
← {"jsonrpc":"2.0","id":3,"result":{"done":false,"events":[
     {"event":"try","column":0,"row":0,"board":[],"seq":0},
     {"event":"place","column":0,"row":0,"board":[0],"seq":1},
     {"event":"try","column":0,"row":1,"board":[0],"seq":2}]}}

… later …
← {"jsonrpc":"2.0","id":40,"result":{"done":true,"events":[
     {"event":"backtrack","column":7,"row":0,"board":[],"seq":33587},
     {"event":"done","seq":33588}]}}

→ {"jsonrpc":"2.0","method":"queens.close","params":{"stream_id":"6f1c…"},"id":41}
← {"jsonrpc":"2.0","result":{"closed":true},"id":41}

→ {"jsonrpc":"2.0","method":"queens.next","params":{"stream_id":"6f1c…"},"id":42}
← {"jsonrpc":"2.0","id":42,"error":{"code":-32001,
     "message":"Stream not found (unknown, closed, or expired)","data":{"stream_id":"6f1c…"}}}
```

## 7. Lifetime, limits, errors

- **IDs:** `uuid4`, unguessable; process-local. A restart invalidates all IDs.
- **open** validates `size ∈ [4,10]` first, then allocates. It forces nothing.
- **next** validates `limit ∈ [1,32]` (default 1) and forces at most `limit`
  cells under the entry's lock, so concurrent requests on one stream receive
  disjoint, ordered events (state update is atomic per request).
- **Exhaustion:** the response containing `done` has `done: true`; the solver
  state (cursor and all closures) is released immediately. A tiny "exhausted"
  record remains so later `next` calls return `{"events": [], "done": true}`.
- **close** removes the record; later calls with that ID get `-32001`.
- **Expiry:** an entry idle for **300 s** (`--ttl`) is removed by a sweep that
  runs at the start of every table operation (open/next/close). Exhausted
  records expire the same way.
- **Cap:** at most 64 open entries; `queens.open` beyond that → `-32002`.
- **Codes:** `-32700` parse error, `-32600` invalid request (also batches),
  `-32601` unknown method, `-32602` invalid params, `-32603` internal error
  (no details), `-32001` stream not found, `-32002` too many streams.
- **HTTP:** 200 for every response, 204 for notifications, 415 wrong
  content type, 413 body > 64 KiB, 404/405 wrong path/method.
- **Safety:** the method table is fixed; no source text or function name from
  a request ever reaches LAMBDA3. Responses contain only JSON events.

## 8. Client

`player.js` keeps a buffer of at most one batch (8 events while playing, 32
during "Next solution") and requests the next batch only when the buffer is
empty. A `generation` counter cancels stale async work after Reset/Restart.
`board.js` is a pure reducer from events to a view (board, highlighted cell,
attacking queens, counters); `main.js` paints it.
