# Assignment #7

## Building a JSON-RPC Service for LAMBDA3

## Due date

**Due: Tuesday, November 10, 2026.**

## Attention

Keep everything you submit in `assigns/07/MySolution/`.

## Objective

Build a JSON-RPC 2.0 service that makes the LAMBDA3 language tools available
to clients over HTTP. A client sends a method name and parameters; the service
returns a result or a structured RPC error. The emphasis is on RPC method
design, request/response envelopes, parameter validation, error handling,
documentation, and automated testing.

## Starting point and scope

Use **Python 3.12 or later** and the provided
[LAMBDA3 implementation](./LAMBDA3/lambda3.py). Study its parser,
type-checker, interpreter, value formatter, and Python and JavaScript
compilers before designing the service. Do not substitute the older
constructor-expression interface from `lambda1.py`.

LAMBDA3 source is text in the language's own syntax. For example:

```text
let fact : sint -> sint =
  fix fact(n: sint): sint =>
    if n <= 1 then 1 else n * fact(n - 1)
in fact(6) end
```

Use `d0exp_parse_and_typecheck` to parse and type-check a source expression.
Use `d0exp_evaluate` for interpretation and `d0val_format` to format its
result. Use `d0exp_compile` or `d0exp_compile_js` to return generated code.
Implementing a new parser, interpreter, type-checker, or compiler is not
required.

Expose one HTTP endpoint, `POST /rpc`, using JSON-RPC 2.0 request and
response objects with the `application/json` media type. Do not model
operations as separate resource URLs. The service is for local development
and automated tests. Accounts, database storage, public deployment, and
execution of generated programs submitted over HTTP are outside scope. The
compiler methods return generated source code as text; they do not execute
it. Lazy-stream delivery across multiple RPC calls is reserved for Assign08.
The language implementation's standard library modules in `LAMBDA3/mylib/`
are part of the provided system and should be available for demonstrations
and tests.

## Required RPC behavior

Implement the following methods (names are case-sensitive):

| RPC method | Parameters | Result |
| --- | --- | --- |
| `service.health` | `{}` | `{ "status": "ok", "version": "1.0" }` |
| `lambda.typecheck` | `{ "source": "..." }` | `{ "type": "sint" }` |
| `lambda.interpret` | `{ "source": "..." }` | `{ "type": "sint", "value": "42" }` |
| `lambda.compile` | `{ "source": "...", "target": "python" }` or `{ "source": "...", "target": "javascript" }` | `{ "target": "python", "code": "..." }` |

Every call request must follow JSON-RPC 2.0: `jsonrpc` is `"2.0"`, `method`
is a string, `params` is an object for these methods, and `id` is a string,
number, or null. A valid request may omit `id` to act as a notification.
Successful responses contain the request's `id` and a `result`; failed
responses contain the `id` and an `error` object with integer `code`, string
`message`, and optional structured `data`. A response must not contain both
`result` and `error`. An invalid request without a usable ID still receives
an Invalid Request response with `id: null`.

Source parameters must carry a nonempty `source` string. Compile results must
identify the target language and return generated code as a string.
Interpretation results must return the type and formatted value; do not
serialize Python closure or environment objects. A function value should use
the representation provided by `d0val_format` (for example, `<lam>` or
`<fix>`). Use `format_type` for returned types and `d0val_format` for
interpreted values. Return generated code unchanged as a string.

All source methods must parse and type-check before interpreting or
compiling. Use the standard JSON-RPC errors for parse error (`-32700`),
invalid request (`-32600`), unknown method (`-32601`), invalid parameters
(`-32602`), and internal error (`-32603`). A LAMBDA source syntax error is an
application error, not a JSON-RPC parse error. Define distinct application
error codes in the server-error range `-32000` through `-32099` for LAMBDA
syntax errors, type-checking errors, and execution timeout. Use `-32010` for
LAMBDA syntax errors, `-32011` for type-checking errors, and `-32012` for
execution timeouts. Do not expose tracebacks or filesystem paths. Return
HTTP 200 for JSON-RPC response objects, including parse and invalid-request
errors; use transport status codes for failures such as unsupported media
types. Document this distinction.

Support JSON-RPC batch requests. Return a response array for a nonempty batch.
Include a response for every valid call request and every invalid batch item;
omit valid notifications. If a batch contains only notifications, return an
empty HTTP body with HTTP status `204`. A single valid notification also
receives no response and uses HTTP status `204`.
Preserve request IDs; clients must match batch responses by ID, not array
position. An invalid request whose ID is missing or invalid receives an
Invalid Request error with `id: null`. An empty batch is an invalid request
and receives a single Invalid Request response object with `id: null`.

Set and document a maximum source size. The LAMBDA3 interpreter is recursive
and does not expose a step budget. Run interpretation with a hard deadline
that can stop the computation (for example, in a worker process that can be
terminated). Handle deadline expiry as an explicit RPC error. A timeout does
not prove nontermination.

## Tasks

### 1. Specify the RPC contract

Create `RPC.md` before implementing the dispatcher. Include:

- The `POST /rpc` transport contract and method table with params, result
  shapes, and behavior.
- Complete JSON-RPC request/response examples for health, successful
  type-checking, successful interpretation, compilation, syntax and type
  errors, a batch containing calls and a notification, and a notification-only
  batch.
- Error categories and their mappings to JSON-RPC error codes and `data`.
- Source-size and interpretation-time limits.
- An explanation of the JSON-RPC envelope, request IDs, batches,
  notifications, and the distinction between HTTP transport status and RPC
  outcome.
- JSON Schema for the request and response envelopes, or an OpenAPI document
  describing the single HTTP transport endpoint and its JSON-RPC payloads.

### 2. Implement the RPC service

Use Flask, FastAPI, or another instructor-approved Python web framework.
Separate JSON-RPC envelope handling from LAMBDA3 operations. The `/rpc`
handler should validate the envelope, dispatch the method to a small service
layer that wraps LAMBDA3, and serialize the JSON-RPC response. It should not
duplicate parser, type-checker, interpreter, or compiler logic.

The required behavior must use these LAMBDA3 operations as appropriate:

```text
d0exp_parse_and_typecheck(source) -> (expression, type)
d0exp_evaluate(expression)         -> value
format_type(type)                  -> string
d0val_format(value)                -> string
d0exp_compile(expression)          -> Python source string
d0exp_compile_js(expression)       -> JavaScript source string
```

Map `LambdaSyntaxError` and `TypeCheckError` to documented application RPC
errors with useful client-facing diagnostics. Unexpected failures should
produce `-32603` and be logged on the server without returning internal
details. Preserve request IDs in applicable responses. Do not use Python
`exec` or JavaScript evaluation to implement an RPC method.

### 3. Test the RPC service

Use automated HTTP-level tests through the framework's test client or an
equivalent in-process client. Assert both HTTP transport behavior and the
JSON-RPC envelope. Cover:

1. `service.health` returns service status and API version and preserves the
   request id.
2. Type-checking valid programs returns the expected formatted type.
3. Interpretation handles arithmetic, factorial, a tuple, and a collection;
   verify formatted value and type.
4. Python and JavaScript compilation return nonempty generated source and the
   correct target-language field.
5. Syntax errors and type errors have distinct documented RPC error codes.
6. Malformed JSON, invalid envelopes, unknown methods, absent or wrongly
   typed params, blank source, and oversized source are handled as specified.
7. A function result is formatted without leaking closure internals.
8. An injected backend failure or timeout returns the documented RPC error,
   preserves the id, and does not disclose a traceback.
9. Demonstrate that LAMBDA3 type-checking rejects an unbound variable; a
   separate lint operation is not required.
10. Batch responses preserve IDs and omit valid notifications. Invalid batch
    members receive Invalid Request responses with `id: null`; a
    notification-only batch produces an empty body; and an empty batch
    receives one Invalid Request response object. A single notification also
    produces no response body and uses the documented HTTP status.

Use test doubles only for failure behavior and dispatch boundaries. Successful
type-check, interpretation, and compilation tests must invoke LAMBDA3.

### 4. Document and demonstrate

Write `README.md` with Python/framework versions, setup, test and startup
commands, endpoint URL, and curl examples for all RPC methods. Demonstrate a
successful factorial request, an unbound-variable or type error, and at least
one compile request. Explain that generated code is returned but not run by
the service.

Write `TESTING.md` mapping required behaviors to test names and recording
observed results. Include a short architecture diagram or dependency sketch
showing the HTTP transport, JSON-RPC dispatcher, service adapter, and LAMBDA3
module.

Write `AI-TRANSCRIPT.md`: record AI tools used, important prompts or
suggestions, and how you reviewed and tested the result. If no AI was used,
state that explicitly.

## Submission

Submit under `MySolution/`:

- RPC implementation and dependency declarations.
- `RPC.md` and a JSON Schema or OpenAPI description.
- Automated HTTP API tests and `TESTING.md`.
- `README.md` with reproducible setup, startup, and usage instructions.
- `AI-TRANSCRIPT.md`.

Do not submit virtual environments, caches, installed dependencies, or
secrets. Verify the documented tests from the assignment directory.

## Evaluation

| Criterion | Weight |
| --- | --- |
| JSON-RPC contract, envelopes, IDs, batches, and error semantics | 25% |
| Correct integration with LAMBDA3 parsing and type-checking | 20% |
| Correct interpretation and Python/JavaScript compilation methods | 20% |
| Parameter validation and information handling | 15% |
| Automated tests, architecture, and reproducible documentation | 20% |

An implementation that treats each operation as a REST resource instead of
dispatching RPC methods, accepts Python constructor expressions instead of
LAMBDA3 source, claims type-check success without calling the LAMBDA3 checker,
or executes generated code over HTTP does not meet the core requirements.

## Optional extensions

After completing the required RPC service, consider a method for parsing a
file of sequential declarations, a client CLI, or a browser-based RPC
explorer. Keep extensions separate from the required contract.
