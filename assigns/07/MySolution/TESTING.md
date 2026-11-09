# Testing

## Architecture

```text
 HTTP client (curl, TEST/test_rpc_api.py, Flask test client)
        │  POST /rpc   Content-Type: application/json
        ▼
┌──────────────────────────────┐
│ app.py  HTTP transport       │  media type (415), body size (413), 404/405,
│ (Flask)                      │  200 + JSON body, or 204 + empty body
└──────────────┬───────────────┘
               │ raw bytes
               ▼
┌──────────────────────────────┐
│ jsonrpc.py  Dispatcher       │  JSON parse (-32700), envelope check (-32600),
│ (no Flask, no LAMBDA3)       │  batches, notifications, id preservation,
│                              │  method lookup (-32601), params object (-32602),
│                              │  unexpected exceptions → log + -32603
└──────────────┬───────────────┘
               │ method(params: dict)
               ▼
┌──────────────────────────────┐        ┌───────────────────────────────┐
│ service.py  LambdaService    │───────▶│ sandbox.py  ProcessInterpreter │
│ param validation, LAMBDA     │ interp │ spawn worker, 5 s deadline,    │
│ errors → -32010/-32011/-32014│        │ terminate → -32012             │
└──────────────┬───────────────┘        └───────────────┬───────────────┘
               │ build / format_type / compile          │ (worker process)
               ▼                                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ backend.py → LAMBDA3/lambda3.py (unchanged) + LAMBDA3/mylib/*.lam      │
│ d0exp_parse_and_typecheck · d0exp_evaluate · d0val_format ·            │
│ format_type · d0exp_compile · d0exp_compile_js                         │
└───────────────────────────────────────────────────────────────────────┘
```

Each layer only calls the one below it. The dispatcher has no idea what
LAMBDA3 is, and the service has no idea what HTTP or JSON-RPC envelopes are.
That is what makes the dispatch-boundary spy tests below possible.

## How to run

From `assigns/07/`:

```bash
MySolution/.venv/Scripts/python -m unittest discover -s MySolution/tests -t MySolution -v
```

With the server running (`MySolution/.venv/Scripts/python MySolution/run.py`):

```bash
python -m unittest discover -s TEST -v
```

All tests in `MySolution/tests/test_rpc_service.py` go through HTTP using
Flask's in-process test client, and check **both** the HTTP status/media type
and the JSON-RPC envelope (`jsonrpc`, `id`, `result` xor `error`, code). Every
HTTP 200 body is also validated against `schema/jsonrpc-lambda.schema.json`,
and every error response is checked for leaks (`Traceback`, `.py`, user paths,
`lambda3`, LAMBDA3 internal class names).

Test doubles are used **only** in `FailureInjectionTests` (failures/timeouts)
and `DispatchBoundaryTests` (a spy method). Every success test for
type-checking, interpretation, and compilation runs the real LAMBDA3 code, and
interpretation runs in real worker processes.

## Requirement → test mapping

Test names are in `MySolution/tests/test_rpc_service.py` (class.method).
"BB" = instructor black-box test in `TEST/test_rpc_api.py`.

| # | Required behavior | Tests |
| --- | --- | --- |
| 1 | `service.health` returns status + version, preserves id | `HealthTests.test_health_returns_status_version_and_preserves_id` (string, number, and null ids), `HealthTests.test_health_rejects_unexpected_params`; BB `test_health` |
| 2 | Type-checking valid programs returns the formatted type | `TypecheckTests.test_typecheck_valid_programs` (sint, bool, tuple, list, function, factorial), `TypecheckTests.test_typecheck_with_mylib_library`; BB `test_typecheck_arithmetic` |
| 3 | Interpretation: arithmetic, factorial, tuple, collection (value + type) | `InterpretTests.test_arithmetic`, `test_factorial`, `test_tuple`, `test_collection_list`, `test_collection_example_program` (LAMBDA3/mytest/collections.lam), `test_collection_with_library`; BB `test_interpret_arithmetic`, `test_interpret_tuple`, `test_interpret_list` |
| 4 | Python and JavaScript compile: nonempty code + correct `target` | `CompileTests.test_python_and_javascript`, `test_code_is_returned_unchanged` (equal to `d0exp_compile` output), `test_compile_still_typechecks_first`, `test_bad_or_missing_target`; BB `test_compile_python_and_javascript` |
| 5 | Syntax vs type errors have distinct codes | `LanguageErrorTests.test_syntax_and_type_errors_have_distinct_codes` (-32010 with line/column, -32011), `test_every_source_method_reports_language_errors` (all 3 source methods), `test_syntax_error_positions_refer_to_user_source_with_libraries`; BB `test_language_syntax_and_type_errors_are_distinct` |
| 6 | Malformed JSON, invalid envelopes, unknown methods, absent/wrong params, blank and oversized source | `EnvelopeAndParamsTests.test_malformed_json_is_parse_error` (truncated, not JSON, bad UTF-8, `NaN`), `test_invalid_envelopes` (11 cases), `test_unknown_method` (incl. wrong case), `test_absent_or_wrongly_typed_params` (missing, array), `test_invalid_source_values` (missing, blank, empty, number, null, list, extra key, bad/duplicate library), `test_oversized_source` (exactly at limit OK, +1 byte rejected), `test_deeply_nested_source_is_resource_limit`; `TransportTests.*` (415, 413, 404, 405); BB `test_invalid_params_and_unknown_method`, `test_malformed_json_returns_parse_error`, `test_invalid_request_and_empty_batch` |
| 7 | Function result formatted without closure internals | `InterpretTests.test_function_values_are_formatted_without_closure_internals` (`<lam>` and `<fix>`, plus leak check); BB `test_interpret_function_formats_closure` |
| 8 | Injected backend failure or timeout → documented error, id preserved, no traceback | `FailureInjectionTests.test_backend_crash_is_internal_error_without_traceback` (error is exactly `{"code": -32603, "message": "Internal error"}`, and the detail **is** in the server log), `test_interpreter_crash_is_internal_error`, `test_injected_timeout_is_reported` (double → -32012), `test_real_worker_is_stopped_at_deadline` (real `fib(40)` with a 1 s limit → -32012, then a normal call still works); also `InterpretTests.test_runtime_error_is_application_error` (-32013), `test_unbounded_recursion_is_resource_limit` (-32014) |
| 9 | Type-checking rejects an unbound variable | `TypecheckTests.test_typecheck_rejects_unbound_variable` (`x + 1` → -32011, "unbound variable 'x'"), `test_library_function_is_unbound_without_library` |
| 10 | Batches: ids preserved, notifications omitted, invalid members → `id: null`, notification-only → empty body, empty batch → one error object, single notification → 204 | `BatchTests.test_batch_preserves_ids_and_omits_notifications` (matched by id; includes a failing call and a notification to an unknown method), `test_invalid_members_get_null_id_errors`, `test_notification_only_batch_is_empty_204`, `test_single_notification_is_empty_204`, `test_failing_notification_is_still_silent`, `test_empty_batch_is_one_invalid_request_object`, `test_batch_size_limit`; BB `test_batch_matches_by_id_and_omits_notification`, `test_notification_only_batch_has_no_response`, `test_notification_has_no_response`, `test_malformed_batch_member_gets_null_id_error` |
| — | Dispatcher/service boundary | `DispatchBoundaryTests.test_params_are_passed_unchanged`, `test_invalid_envelope_never_reaches_a_method`, `test_notifications_still_run` |

## Observed results

Recorded on Windows 11, Python 3.14.0, Flask 3.1.3, on 2026-11-08.

**My suite:**

```text
$ MySolution/.venv/Scripts/python -m unittest discover -s MySolution/tests -t MySolution -v
...
Ran 47 tests in 6.5s

OK
```

**Instructor black-box suite** against `MySolution/run.py` on port 8000:

```text
$ python -m unittest discover -s TEST -v
...
Ran 15 tests in 2.2s

OK
```

**Manual curl checks** (exact responses are in README.md and RPC.md §6):
health, typecheck, factorial → `720`, Python and JavaScript compile, syntax
error -32010, unbound variable -32011, runtime error -32013, batch with a
notification, notification-only batch → HTTP 204, wrong `Content-Type` → HTTP
415. A `fib(40)` call was stopped at the deadline with -32012.

## Problems found while testing

* **Worker crashed on Windows.** The first black-box run had 5 interpret
  failures (-32603). The server log showed `threading.stack_size(256 MiB)`
  raising `ValueError: size not valid` in the worker on Windows. Fixed by
  using 128 MiB and falling back to the default stack if the platform still
  refuses. The -32603 response leaked nothing, as designed.
* **Huge results.** `fact(3000)` produced a number too long for Python's
  int-to-string limit, and was first reported as a LAMBDA runtime error
  (-32013). It is a size problem, not a program bug, so formatting failures
  are now reported as -32014 (resource limit).
