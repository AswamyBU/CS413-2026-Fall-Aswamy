# LAMBDA3 JSON-RPC Contract (API version 1.0)

This document is the contract for the LAMBDA3 RPC service. It was written
before the dispatcher; the implementation and tests follow it.

## 1. Transport

| Item | Value |
| --- | --- |
| Endpoint | `POST /rpc` (the only endpoint) |
| Default URL | `http://127.0.0.1:8000/rpc` |
| Request media type | `Content-Type: application/json` (parameters such as `; charset=utf-8` are allowed). Body must be UTF-8 JSON. |
| Response media type | `application/json` for every JSON-RPC response |
| Protocol | [JSON-RPC 2.0](https://www.jsonrpc.org/specification) |

Operations are **methods named inside the request body**, not URLs. There is
no `/typecheck`, `/interpret`, etc.

### HTTP status vs. RPC outcome

HTTP status describes only whether the **transport** worked. Whether the
*call* worked is in the JSON-RPC body.

| HTTP status | When | Body |
| --- | --- | --- |
| **200** | The server produced a JSON-RPC response: a success, **or any RPC error**, including Parse error (-32700), Invalid Request (-32600), LAMBDA syntax/type errors, timeouts | JSON-RPC response object or array |
| **204** | Nothing to answer: a single valid notification, or a batch made only of valid notifications | empty |
| 404 | Any URL other than `/rpc` | `text/plain` |
| 405 | `/rpc` with a method other than POST | `text/plain` |
| 413 | Body larger than 1 MiB | `text/plain` |
| 415 | `Content-Type` is not `application/json` | `text/plain` |

So a client must not treat "HTTP 200" as "the call succeeded": it must look
for `result` vs `error`. Conversely, 4xx responses are not JSON-RPC
responses, and contain no `id`.

## 2. Envelopes, IDs, notifications, batches

**Request object** (all members except `id` required for this service):

```json
{ "jsonrpc": "2.0", "method": "lambda.typecheck", "params": { "source": "1 + 2" }, "id": 1 }
```

* `jsonrpc` must be exactly the string `"2.0"`.
* `method` is a nonempty, case-sensitive string.
* `params` must be an **object** (by-name). JSON-RPC also allows arrays,
  so an array passes the envelope check but is rejected with -32602.
  A missing `params` is also -32602.
* `id` is a string, number, or `null` (booleans, objects, arrays are invalid).
* No other members are allowed.

**Response object.** Exactly one of `result` / `error` is present, never both.
`id` is the request's `id`, copied unchanged (type included: `7` stays `7`,
`"7"` stays `"7"`).

```json
{ "jsonrpc": "2.0", "result": { "type": "sint" }, "id": 1 }
{ "jsonrpc": "2.0", "error": { "code": -32011, "message": "...", "data": { } }, "id": 1 }
```

**IDs on errors.** If the body is not JSON (-32700) or the request object is
invalid (-32600), the server cannot trust anything inside it, so the response
`id` is always `null`, even if the bad request carried an id-like value.
For every other error (unknown method, bad params, LAMBDA errors, timeout,
internal) the request's `id` is preserved.

**Notifications.** A *valid* request with no `id` member is a notification:
the method runs, but nothing is returned, even if it fails. (`"id": null`
is *not* a notification; it gets a response with `id: null`.) An *invalid*
request without an `id` is not a valid notification, so it still gets an
Invalid Request response with `id: null`.

**Batches.** A body may be a JSON array of request objects (1 to 50 items).

* Each item is handled independently, in order.
* The response is an array containing one response per call **and** one
  Invalid Request (`id: null`) per invalid item; valid notifications are
  omitted.
* Clients must match responses to requests **by `id`, not by position**.
  (Duplicate ids in one batch are allowed but make matching ambiguous; avoid them.)
* If every item is a valid notification, the reply is HTTP 204 with an empty body.
* An empty array `[]` is itself an Invalid Request: the reply is a **single**
  error object (not an array) with `id: null`.
* More than 50 items is also a single Invalid Request object.

## 3. Methods

All names are case-sensitive. "Source params" are:

| Param | Type | Required | Notes |
| --- | --- | --- | --- |
| `source` | string | yes | LAMBDA3 source text for **one expression**. Must contain a non-whitespace character. At most **65,536 UTF-8 bytes**. |
| `libraries` | array of strings | no | Any of `"list"`, `"optn"`, `"a1sz"`, `"strm"` (no duplicates). Binds the declarations from `LAMBDA3/mylib/<name>.lam` around the source. Default `[]`. |

Unknown params are rejected with -32602.

| Method | Params | Result | Behavior |
| --- | --- | --- | --- |
| `service.health` | `{}` (must be empty) | `{"status": "ok", "version": "1.0"}` | Liveness and API version. Does not touch LAMBDA3. |
| `lambda.typecheck` | source params | `{"type": "<type>"}` | `d0exp_parse_and_typecheck(source)`, then `format_type(type)`. |
| `lambda.interpret` | source params | `{"type": "<type>", "value": "<value>"}` | Parse and type-check first (errors returned without running anything). Then, in a separate worker process with a deadline, `d0exp_evaluate` and `d0val_format`. Functions appear as `<lam>` / `<fix>`; no closure or environment is ever serialized. Output of LAMBDA `print` is discarded. |
| `lambda.compile` | source params + `target` (`"python"` or `"javascript"`, required) | `{"target": "<target>", "code": "<program>"}` | Parse and type-check first, then `d0exp_compile` or `d0exp_compile_js`. The generated program is returned unchanged as a string and is **never executed** by the service. |

When `libraries` is used, the user source is parsed alone (so syntax-error
line/column refer to the user's text), wrapped as
`D0Elets(<library declarations>, <expression>)` exactly as
`mylib/TEST` does, and that whole expression is type-checked, interpreted or
compiled.

Types come from `format_type`, e.g. `sint`, `bool`, `(sint, bool)`,
`List[sint]`, `sint -> sint`. Unconstrained type variables print like
`?t0 -> ?t0`.

## 4. Errors

### Error codes

| Code | Message (prefix) | Category | When | `data` |
| --- | --- | --- | --- | --- |
| -32700 | `Parse error` | JSON-RPC | Body is not valid UTF-8 JSON (`NaN`/`Infinity` are rejected too). | none |
| -32600 | `Invalid Request` | JSON-RPC | Not a valid request object; empty batch; batch over 50 items. `id` is always `null`. | `{"reason": "..."}` or batch limit info |
| -32601 | `Method not found` | JSON-RPC | Unknown method name (case-sensitive). | `{"method": "...", "available": [...]}` |
| -32602 | `Invalid params: ...` | JSON-RPC | `params` missing or an array; missing/non-string/blank/oversized `source`; bad `target`; bad `libraries`; unexpected keys. | Details, e.g. `{"limit": "maxSourceBytes", "maxSourceBytes": 65536, "actualBytes": 70000}` |
| -32603 | `Internal error` | JSON-RPC | Any unexpected server failure. Details are **logged on the server only**. | none |
| **-32010** | `LAMBDA syntax error at line L, column C: ...` | Application | `LambdaSyntaxError` from the LAMBDA3 parser. | `{"stage": "parse", "message", "line", "column", "sourceLine"}` |
| **-32011** | `LAMBDA type error: ...` | Application | `TypeCheckError` from the LAMBDA3 checker (including unbound variables). | `{"stage": "typecheck", "message"}` |
| **-32012** | `Interpretation exceeded the N second limit and was stopped` | Application | Interpretation deadline expired; the worker was terminated. | `{"timeoutSeconds": N, "note": "A timeout does not prove that the program never terminates."}` |
| -32013 | `LAMBDA runtime error: ...` | Application | A well-typed program failed while running: `list_head`/`list_tail`/`optn_get` of an empty value, division by zero, array index out of range, negative array size. | `{"exception": "ValueError", "message": "..."}` |
| -32014 | `Resource limit exceeded` variants | Application | Recursion too deep (in parse/type-check/compile/evaluation), or a result too large to format (over 1,048,576 characters, or an integer with more than 4300 digits). | `{"limit": "recursionDepth" \| "maxValueChars", ...}` |

A LAMBDA syntax error is **not** a JSON-RPC parse error: -32700 is only about
the JSON body; bad LAMBDA source inside a well-formed request is -32010.

### Information handling

Error responses never contain Python tracebacks, file paths, exception
`repr`s, or internal objects. LAMBDA diagnostics (syntax position, type error
text, runtime message) are returned because they describe the client's own
program. Runtime messages are truncated to 300 characters.

## 5. Limits

| Limit | Default | Env override | Exceeded → |
| --- | --- | --- | --- |
| `source` size | 65,536 UTF-8 bytes | `LAMBDA_RPC_MAX_SOURCE_BYTES` | -32602 |
| HTTP body size | 1,048,576 bytes | `LAMBDA_RPC_MAX_BODY_BYTES` | HTTP 413 |
| Batch items | 50 | `LAMBDA_RPC_MAX_BATCH` | -32600 |
| Interpretation time | **5 seconds** of evaluation per call | `LAMBDA_RPC_TIMEOUT` | -32012 |
| Worker start-up | 20 seconds (not counted in the 5 s) | — | -32603 |
| Recursion depth | 100,000 Python frames in the worker | — | -32014 |
| Formatted value | 1,048,576 characters | — | -32014 |

**How the deadline works.** The LAMBDA3 interpreter is recursive and has no
step budget, so each `lambda.interpret` call runs `d0exp_evaluate` in a fresh
`multiprocessing` *spawn* worker process. The worker signals "ready" after
starting; the server then waits at most 5 seconds for the result and
**terminates the process** if it has not finished. Only strings cross the
process boundary. The timer is wall-clock time, so a busy machine can time out
a program that would finish elsewhere: **a timeout does not prove
nontermination.** Batches run sequentially, so a batch of N interpret calls
can take up to N × 5 seconds.

Type-checking and compilation run in the server process; they are bounded by
the source size limit and the recursion-depth guard.

## 6. Examples

All examples are `POST /rpc` with `Content-Type: application/json`, and were
captured from the running service (long code strings shortened with `...`).

**Health**

```json
→ {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": "health-1"}
← 200 {"jsonrpc": "2.0", "result": {"status": "ok", "version": "1.0"}, "id": "health-1"}
```

**Successful type-check**

```json
→ {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "lam (x: sint) => x * 2"}, "id": 2}
← 200 {"jsonrpc": "2.0", "result": {"type": "sint -> sint"}, "id": 2}
```

**Successful interpretation (factorial)**

```json
→ {"jsonrpc": "2.0", "method": "lambda.interpret",
   "params": {"source": "let fact : sint -> sint =\n  fix fact(n: sint): sint =>\n    if n <= 1 then 1 else n * fact(n - 1)\nin fact(6) end"},
   "id": 3}
← 200 {"jsonrpc": "2.0", "result": {"type": "sint", "value": "720"}, "id": 3}
```

**Interpretation with a library, and a function value**

```json
→ {"jsonrpc": "2.0", "method": "lambda.interpret",
   "params": {"source": "list_reverse(list_cons(1, list_cons(2, list_nil())))", "libraries": ["list"]}, "id": 9}
← 200 {"jsonrpc": "2.0", "result": {"type": "List[sint]", "value": "[2, 1]"}, "id": 9}

→ {"jsonrpc": "2.0", "method": "lambda.interpret",
   "params": {"source": "let f : sint -> sint = lam (x: sint) => x in f end"}, "id": 5}
← 200 {"jsonrpc": "2.0", "result": {"type": "sint -> sint", "value": "<lam>"}, "id": 5}
```

**Compilation**

```json
→ {"jsonrpc": "2.0", "method": "lambda.compile", "params": {"source": "1 + 2", "target": "python"}, "id": 4}
← 200 {"jsonrpc": "2.0", "result": {"target": "python",
        "code": "...def _lambda_main():\n    _v1 = 1\n    _v2 = 2\n    _v3 = (_v1 + _v2)\n    return _v3\n\n_lambda_result = _lambda_main()\n"},
       "id": 4}
```

`"target": "javascript"` returns the same shape with JavaScript in `code`.

**LAMBDA syntax error**

```json
→ {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "if then"}, "id": 5}
← 200 {"jsonrpc": "2.0", "error": {"code": -32010,
        "message": "LAMBDA syntax error at line 1, column 4: Expected an expression",
        "data": {"stage": "parse", "message": "Expected an expression", "line": 1, "column": 4, "sourceLine": "if then"}},
       "id": 5}
```

**LAMBDA type errors (mismatch, unbound variable)**

```json
→ {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "1 + true"}, "id": 7}
← 200 {"jsonrpc": "2.0", "error": {"code": -32011, "message": "LAMBDA type error: +: expected bool, got sint",
        "data": {"stage": "typecheck", "message": "+: expected bool, got sint"}}, "id": 7}

→ {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "x + 1"}, "id": 6}
← 200 {"jsonrpc": "2.0", "error": {"code": -32011, "message": "LAMBDA type error: unbound variable 'x'",
        "data": {"stage": "typecheck", "message": "unbound variable 'x'"}}, "id": 6}
```

**Timeout**

```json
→ {"jsonrpc": "2.0", "method": "lambda.interpret",
   "params": {"source": "let fib : sint -> sint = fix fib(n: sint): sint => if n < 2 then n else fib(n - 1) + fib(n - 2) in fib(40) end"},
   "id": "fib"}
← 200 {"jsonrpc": "2.0", "error": {"code": -32012,
        "message": "Interpretation exceeded the 5 second limit and was stopped",
        "data": {"timeoutSeconds": 5.0, "note": "A timeout does not prove that the program never terminates."}},
       "id": "fib"}
```

**Batch with calls and a notification** (the notification gets no response)

```json
→ [{"jsonrpc": "2.0", "method": "lambda.interpret", "params": {"source": "6 * 7"}, "id": "a"},
   {"jsonrpc": "2.0", "method": "service.health", "params": {}},
   {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "(1, true)"}, "id": "b"}]
← 200 [{"jsonrpc": "2.0", "result": {"type": "sint", "value": "42"}, "id": "a"},
       {"jsonrpc": "2.0", "result": {"type": "(sint, bool)"}, "id": "b"}]
```

**Batch with an invalid member**

```json
→ [{"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": "ok"}, "not-a-request-object"]
← 200 [{"jsonrpc": "2.0", "result": {"status": "ok", "version": "1.0"}, "id": "ok"},
       {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request: request must be a JSON object",
        "data": {"reason": "request must be a JSON object"}}, "id": null}]
```

**Notification-only batch, and a single notification**

```json
→ [{"jsonrpc": "2.0", "method": "service.health", "params": {}},
   {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "1 + 2"}}]
← 204 (empty body)

→ {"jsonrpc": "2.0", "method": "service.health", "params": {}}
← 204 (empty body)
```

**Envelope errors**

```json
→ {"jsonrpc":                       (truncated JSON)
← 200 {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error: body is not valid JSON"}, "id": null}

→ []
← 200 {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request: batch must not be empty"}, "id": null}

→ {"jsonrpc": "1.0", "method": "service.health", "params": {}, "id": 1}
← 200 {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request: jsonrpc must be exactly \"2.0\"",
        "data": {"reason": "jsonrpc must be exactly \"2.0\""}}, "id": null}

→ {"jsonrpc": "2.0", "method": "lambda.lint", "params": {}, "id": "u"}
← 200 {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found",
        "data": {"method": "lambda.lint", "available": ["lambda.compile", "lambda.interpret", "lambda.typecheck", "service.health"]}}, "id": "u"}

→ {"jsonrpc": "2.0", "method": "lambda.interpret", "params": {"source": "   "}, "id": 10}
← 200 {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params: 'source' must not be blank"}, "id": 10}
```

## 7. JSON Schema

[`schema/jsonrpc-lambda.schema.json`](schema/jsonrpc-lambda.schema.json)
(JSON Schema 2020-12) defines:

* `#/$defs/requestBody`: one request, or a batch of 1–50 requests, with
  per-method `params` shapes.
* `#/$defs/responseBody`: one response, or an array of responses. A response
  is either `successResponse` (with `result`) or `errorResponse` (with
  `error`), and `additionalProperties: false` forbids having both.
* Result shapes for each method and the error object with its allowed codes.

The automated tests validate **every** HTTP 200 response body against
`responseBody`.

Schema limits the server checks itself (not expressible in plain JSON Schema):
the 65,536-byte UTF-8 size of `source`, and that `params` absent or as an array
is -32602 rather than -32600.
