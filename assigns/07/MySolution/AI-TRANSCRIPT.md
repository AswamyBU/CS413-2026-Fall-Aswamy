# AI Transcript

## Tools used

* **Claude Code** (Anthropic, model Claude Opus 5.5), in the Claude desktop
  app, working directly in this repository.

## Prompt

> Please look at the Assing07 md file as well as the requirements.txt and complete the assignment. Provide necessary diagrams and commands for the README, as well as write what you did for the AI-Transcript. 

>How does this program work? Please walk me through.

>Make sure the tests you created run properly, as well as provide me the commands to run them myself as a final check. 

## What the AI did

1. Read `Assign07.md`, `TEST/README.md`, `TEST/test_rpc_api.py`, and the
   relevant parts of `LAMBDA3/lambda3.py` (value formatter, parser, error
   classes, `d0exp_parse_and_typecheck`, compilers) and `LAMBDA3/mylib/`.
2. Probed LAMBDA3 directly in Python to see which exceptions it raises for
   syntax errors, type errors (including unbound variables), runtime failures
   (`list_head(list_nil())`, `1 / 0`), and infinite recursion, and checked that
   the `mylib/*.lam` libraries are closed and type-check.
3. Chose the design:
   * Flask for the transport only; a framework-free JSON-RPC dispatcher; a
     small service layer that calls LAMBDA3; a separate sandbox module.
   * Interpretation runs in a fresh `spawn` worker process per call so it can
     be terminated after the deadline (LAMBDA3 has no step budget).
   * Extra application codes -32013 (runtime error) and -32014 (resource
     limit) in addition to the required -32010/-32011/-32012.
   * Invalid Request responses always use `id: null`, because the provided
     black-box test expects that even when the bad request has an `id`.
   * Optional `libraries` param to make `mylib/` usable from RPC calls.
4. Wrote `RPC.md`, the JSON Schema, the implementation, the test suite,
   `README.md`, `TESTING.md`, and this file.

## Suggestions I should review

* The `libraries` parameter is an extension beyond the required contract.
* Choice of extra error codes (-32013, -32014) and the limit values
  (64 KiB source, 5 s interpretation, 50-item batches, 1 MiB body).
* Output from LAMBDA `print` is discarded during interpretation.

## How the result was reviewed and tested

* Ran the instructor's black-box suite (`TEST/test_rpc_api.py`) against the
  running server. The first run found a Windows-only worker crash (thread stack
  size too large), which was fixed; then 15/15 passed.
* Wrote 47 HTTP-level tests with the Flask test client covering all ten
  required behaviors, validating every response against the JSON Schema and
  checking error bodies for tracebacks and paths. 47/47 pass.
* Exercised every method by hand with curl against the running server; those
  real responses are the examples in README.md and RPC.md.
* Checked a real timeout (`fib(40)` with a short deadline) and that the server
  keeps working afterward.
