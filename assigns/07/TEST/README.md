# Assign07 RPC contract tests

These are black-box tests for an Assign07 service. They do not depend on Flask,
FastAPI, or another web framework, but they do require the service to be
running.

Start the service using its documented command, then run from
`assigns/07/`:

```sh
python3 -m unittest discover -s TEST -v
```

The default endpoint is `http://127.0.0.1:8000/rpc`. Set
`LAMBDA_RPC_URL` to use another URL:

```sh
LAMBDA_RPC_URL=http://127.0.0.1:9000/rpc python3 -m unittest discover -s TEST -v
```

The suite checks result shapes for health, type-checking, interpretation, and
compilation; JSON-RPC error envelopes; notifications and batches; and basic
parameter validation. It assumes the result shapes and error codes specified
in `../Assign07.md`. It does not test timeout behavior or configurable source
size limits, since those limits are chosen and documented by each
implementation.
