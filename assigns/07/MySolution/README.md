# Assign07: JSON-RPC Service for LAMBDA3

A JSON-RPC 2.0 service that exposes the provided LAMBDA3 parser, type-checker,
interpreter, and Python/JavaScript compilers over one HTTP endpoint,
`POST /rpc`. The full contract (methods, errors, limits, schema) is in
[RPC.md](RPC.md); tests and architecture are in [TESTING.md](TESTING.md).

## Versions

| Component | Version used |
| --- | --- |
| Python | 3.14.0 (3.12 or later required by LAMBDA3) |
| Flask | 3.1.3 (Werkzeug 3.1.9) |
| jsonschema | 4.26.0 (tests only) |
| OS tested | Windows 11 |

## Layout

```text
MySolution/
  run.py                     start the server
  requirements.txt           Flask (+ jsonschema for tests)
  lambda_rpc/
    app.py                   HTTP transport (Flask): POST /rpc, status codes
    jsonrpc.py               JSON-RPC envelopes, batches, notifications, errors
    service.py               the 4 RPC methods: param checks + LAMBDA3 calls
    sandbox.py               interpretation in a worker process with a deadline
    backend.py               imports ../LAMBDA3/lambda3.py and mylib/*.lam
    errors.py, config.py     error codes; limits
  schema/jsonrpc-lambda.schema.json
  tests/test_rpc_service.py  HTTP-level tests (Flask test client)
  RPC.md  TESTING.md  AI-TRANSCRIPT.md
```

The service uses `../LAMBDA3/` unchanged. Set `LAMBDA3_DIR` to use a copy
somewhere else.

## Setup

Run everything from the assignment directory, `assigns/07/`.

Windows (PowerShell):

```bash
python -m venv MySolution\.venv
```

```bash
MySolution\.venv\Scripts\python -m pip install -r MySolution\requirements.txt
```

macOS / Linux:

```bash
python3 -m venv MySolution/.venv && MySolution/.venv/bin/python -m pip install -r MySolution/requirements.txt
```

Commands below use the Windows venv path `MySolution/.venv/Scripts/python`
(works in PowerShell and Git Bash). On macOS/Linux use
`MySolution/.venv/bin/python` instead.

## Run the tests

My HTTP-level tests (in-process Flask test client; no server needed, ~7 s):

```bash
MySolution/.venv/Scripts/python -m unittest discover -s MySolution/tests -t MySolution -v
```

The instructor's black-box tests (need the server running, see below):

```bash
python -m unittest discover -s TEST -v
```

## Start the server

```bash
MySolution/.venv/Scripts/python MySolution/run.py
```

It listens on `http://127.0.0.1:8000/rpc` (only on localhost). Options:
`--port 9000`, `--host`. Limits can be changed with environment variables,
e.g. `LAMBDA_RPC_TIMEOUT=2` (see RPC.md §5). Stop with Ctrl+C.

## curl examples

The examples use bash-style quoting (Git Bash, macOS, Linux). Every response
below was captured from the running server. On Windows PowerShell, use
`curl.exe` and put the JSON in a file: `curl.exe ... -d "@req.json"`.

**service.health**

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"service.health","params":{},"id":"health-1"}' http://127.0.0.1:8000/rpc
```

```json
{"jsonrpc": "2.0", "result": {"status": "ok", "version": "1.0"}, "id": "health-1"}
```

**lambda.typecheck**

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"lam (x: sint) => x * 2"},"id":2}' http://127.0.0.1:8000/rpc
```

```json
{"jsonrpc": "2.0", "result": {"type": "sint -> sint"}, "id": 2}
```

**lambda.interpret: factorial**

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"let fact : sint -> sint =\n  fix fact(n: sint): sint =>\n    if n <= 1 then 1 else n * fact(n - 1)\nin fact(6) end"},"id":3}' http://127.0.0.1:8000/rpc
```

```json
{"jsonrpc": "2.0", "result": {"type": "sint", "value": "720"}, "id": 3}
```

**lambda.interpret with a mylib library**

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"list_reverse(list_cons(1, list_cons(2, list_nil())))","libraries":["list"]},"id":9}' http://127.0.0.1:8000/rpc
```

```json
{"jsonrpc": "2.0", "result": {"type": "List[sint]", "value": "[2, 1]"}, "id": 9}
```

**lambda.compile: Python and JavaScript**

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"1 + 2","target":"python"},"id":4}' http://127.0.0.1:8000/rpc
```

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"1 + 2","target":"javascript"},"id":5}' http://127.0.0.1:8000/rpc
```

```json
{"jsonrpc": "2.0", "result": {"target": "python", "code": "...def _lambda_main():\n    _v1 = 1\n    _v2 = 2\n    _v3 = (_v1 + _v2)\n    return _v3\n\n_lambda_result = _lambda_main()\n"}, "id": 4}
```

The `code` string is a complete program (runtime helpers + `_lambda_main`).
**The service only returns generated code; it never runs it.** To try it,
save the string to a file yourself and run it with `python` or `node`.

**Unbound variable (type error)**

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"x + 1"},"id":6}' http://127.0.0.1:8000/rpc
```

```json
{"jsonrpc": "2.0", "error": {"code": -32011, "message": "LAMBDA type error: unbound variable 'x'", "data": {"stage": "typecheck", "message": "unbound variable 'x'"}}, "id": 6}
```

**Syntax error**

```bash
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"if then"},"id":5}' http://127.0.0.1:8000/rpc
```

```json
{"jsonrpc": "2.0", "error": {"code": -32010, "message": "LAMBDA syntax error at line 1, column 4: Expected an expression", "data": {"stage": "parse", "message": "Expected an expression", "line": 1, "column": 4, "sourceLine": "if then"}}, "id": 5}
```

**Batch with a notification**, and a **notification-only** request (HTTP 204, no body):

```bash
curl -s -H "Content-Type: application/json" -d '[{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"6 * 7"},"id":"a"},{"jsonrpc":"2.0","method":"service.health","params":{}}]' http://127.0.0.1:8000/rpc
```

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"service.health","params":{}}' http://127.0.0.1:8000/rpc
```

## HTTP status vs. RPC result

Every JSON-RPC response, **including errors** like bad JSON (-32700), an
invalid request (-32600), or a LAMBDA type error, uses HTTP **200**; check
`result` / `error` in the body. HTTP 204 means "nothing to send back"
(notifications). 4xx codes are transport problems only: 415 wrong
`Content-Type`, 413 body over 1 MiB, 405 not POST, 404 not `/rpc`. Details are
in RPC.md §1.

## Limits

`source` ≤ 64 KiB (65,536 UTF-8 bytes), request body ≤ 1 MiB, batch ≤ 50
items, interpretation ≤ 5 s per call (worker process is terminated after
that; error -32012). See RPC.md §5.

## Notes

* Output from LAMBDA `print(...)` during interpretation is discarded; only the
  final value is returned.
* Optional extension: the `libraries` parameter (binds `mylib/*.lam`). The
  four required method shapes are unchanged when it is omitted.
