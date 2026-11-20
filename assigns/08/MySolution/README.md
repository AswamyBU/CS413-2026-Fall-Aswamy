# Assign08: Animated N-Queens Search with CPS and Lazy Streams

A LAMBDA3 program searches for N-Queens solutions in continuation-passing
style and exposes every step (try, place, reject, backtrack, solution, done)
as a lazy stream. A JSON-RPC service forces that stream a few cells at a time,
and a browser page animates the events as it pulls them.

See [DESIGN.md](DESIGN.md) for the CPS conventions, laziness argument, and
architecture diagram, and [TESTING.md](TESTING.md) for the requirement → test
map.

## Requirements

- **Python 3.12 or later** (developed and tested on Python 3.14.0, Windows 11).
- **No third-party Python packages.** Everything uses the standard library;
  `requirements.txt` is intentionally empty of packages.
- The supplied LAMBDA3 implementation at `assigns/08/LAMBDA3/` (found
  automatically; override with the environment variable `QUEENS_LAMBDA3_DIR`).
- **Node.js 20+** only for the client unit tests (tested with v24.11.1). No npm
  install.
- Any modern browser for the UI.

## Setup

Nothing to install. From the **assignment directory** (`assigns/08`):

```bash
python --version
```

## Run

```bash
python MySolution/run.py
```

Then open **http://127.0.0.1:8000/**.

Options: `--port 8000`, `--host 127.0.0.1`, `--ttl 300` (idle stream lifetime
in seconds), `--backend compiled|interpreter`. `compiled` (default) runs
`queens.lam` through LAMBDA3's own Python code generator; `interpreter` runs
the same checked program with the reference tree-walking interpreter. It gives
identical output but is about 150× slower: a full 8×8 run takes about 20 s.

## Test

From the assignment directory:

```bash
python -m unittest discover -s MySolution/tests -t MySolution -v
```

```bash
node --test "MySolution/tests/js/*.test.mjs"
```

Optional slow test (full 8×8 trace through the interpreter, about 20 s):

```bash
QUEENS_SLOW_TESTS=1 python -m unittest discover -s MySolution/tests -t MySolution -k full_8x8
```

(PowerShell: `$env:QUEENS_SLOW_TESTS=1; python -m unittest discover -s MySolution/tests -t MySolution -k full_8x8`.)

The browser checklist in TESTING.md covers the DOM layer.

## Controls

| Control | Action |
| --- | --- |
| **Start / Restart** | Opens a fresh search stream (`queens.open`) for the selected board size. Fetches no events yet. |
| **Step** | Shows the next event. |
| **Play / Pause** | Plays one event per tick at the chosen speed, or pauses. |
| **Next solution** | Runs without delay until the next `solution` (or `done`). |
| **Reset** | Closes the stream on the server and clears the board. |
| **Board** | Size 4–10 (8 by default). Changing it resets. |
| **Speed** | 0–1000 ms per event while playing. |
| **Restart search** | Appears after the search completes. |

Visual states: blue outline with `?` = **try**, green = **place**, red `✕` =
**reject** (attacking queens get an orange outline), faded purple =
**backtrack** (the removed queen), gold = **solution**. The status bar
distinguishes "Solution #k found." from "Search complete: N solutions, no
more remain." Counters show solutions, events, tries, rejects, and backtracks.
RPC and network failures show a red banner. An expired or closed stream gets
a message telling you to restart.

## RPC examples

```bash
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"service.health","params":{},"id":1}'
```

```bash
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"queens.open","params":{"size":8},"id":2}'
```

```bash
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"queens.next","params":{"stream_id":"PASTE-ID","limit":3},"id":3}'
```

```bash
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"queens.close","params":{"stream_id":"PASTE-ID"},"id":4}'
```

`queens.next` returns, for example:

```json
{"jsonrpc":"2.0","id":3,"result":{"done":false,"events":[
  {"event":"try","column":0,"row":0,"board":[],"seq":0},
  {"event":"place","column":0,"row":0,"board":[0],"seq":1},
  {"event":"try","column":0,"row":1,"board":[0],"seq":2}]}}
```

| Method | Params | Result |
| --- | --- | --- |
| `service.health` | `{}` (may be omitted) | `{"status":"ok","version":"1.0"}` |
| `queens.open` | `{"size": 4..10}` | `{"stream_id": uuid, "size": n}` |
| `queens.next` | `{"stream_id", "limit": 1..32}` (`limit` defaults to 1) | `{"events": [...], "done": bool}` |
| `queens.close` | `{"stream_id"}` | `{"closed": true}` |

Application errors: **`-32001` Stream not found** (unknown, closed, or
expired id; `data.stream_id` echoes it), **`-32002` Too many open streams**
(cap 64). Standard codes: -32700, -32600, -32601, -32602, -32603. Streams
expire after **300 s** without a request.

## Layout

```text
MySolution/
  run.py                 start the server
  queens/queens.lam      LAMBDA3 CPS search + lazy event stream
  queens/solver.py       load/type-check queens.lam; compiled & interpreter backends; EventStream
  queens/streams.py      stream table: ids, locks, exhaustion, close, expiry
  queens/service.py      RPC methods and parameter validation
  queens/jsonrpc.py      JSON-RPC 2.0 envelope / dispatch
  queens/errors.py       error codes
  queens/server.py       stdlib HTTP server: POST /rpc + static client
  web/                   index.html, style.css, rpc.js, board.js, player.js, main.js
  tests/                 Python unittest suites; tests/js/ Node client tests
```

## Limitations

- **Batches are not supported.** A JSON array body gets one `-32600` response.
- Stream state is in-memory and process-local. Restarting the server
  invalidates every stream id, and nothing persists across browser reloads.
- Notifications run normally but return nothing. A `queens.next`
  notification therefore advances the stream and those events are lost to the
  client.
- After `done`, a small "exhausted" record stays until `queens.close` or
  expiry, so that repeated `next` calls can answer `done: true`. The solver
  state is released immediately.
- The interpreter backend is slow for full traces (about 20 s for 8×8). A
  10×10 full trace has over 200,000 events, so the UI can step through it but
  playing it to the end takes a long time.
- Local use only: no authentication, no TLS, binds to 127.0.0.1 by default.
