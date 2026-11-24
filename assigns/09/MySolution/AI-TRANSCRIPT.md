# AI Transcript

## Tools used

* **Claude Code** (Anthropic, model Claude Opus 5.5), in the Claude desktop
  app, working directly in this repository with file, shell, and in-app
  browser access.

## Prompt
> Please look at Assign09.md and build the program as specified by the requirements. For the AI-Transcript, please write down what you have completed, for the README specify any required commands. 

> Can you please run the tests that you have created, and show me the results. 

>Can you provide the commands I need to run my own test cases.

I also asked the agent to run sanity checks on the finished work and to run
its own automated tests, and then I ran the tests myself.

## What the AI did

1. Read `Assign09.md`, my Assign07 service (`lambda_rpc/`: app factory,
   service layer, error codes, LAMBDA3 locator, sandbox), and the Assign03
   folder. Assign03 contains a requirements document and no UI code, so a
   small studio client was built instead.
2. Wrote the contract first: `API.md` and `openapi.json` (OpenAPI 3.1). They
   cover the route table, schemas, examples, status and error codes, check
   order, uniqueness, limits, pagination snapshots, revision rules, and
   in-memory lifetime.
3. Implemented the database service (`studio_db/`) in separate layers:
   * HTTP routes (`api.py`);
   * request validation (`validation.py`);
   * business rules with one lock per mutation (`service.py`);
   * snapshot cursors (`pagination.py`);
   * a small `Store` interface with an in-memory dict backend (`store.py`);
   * immutable record values (`records.py`).
4. Chose the design:
   * Records are frozen dataclasses. Updates store a new value, so a list
     snapshot just keeps references, and later pages show exactly what
     existed at the first page.
   * The route reads the request body before taking the lock. Parsing and
     validation happen inside the lock, so the documented order
     (404 → 428 → If-Match format → 415/400 → 409) holds and failed requests
     change nothing.
   * IDs are `prg_`/`col_`/`case_` plus 16 hex characters. Malformed IDs are
     `400`; unknown IDs are `404`.
   * Added the error codes `method_not_allowed`, `payload_too_large`,
     `unsupported_media_type`, and `precondition_required` alongside the
     required ones.
5. Built the studio (`web/`):
   * `storage.js` is the only module with REST details;
   * `lambda.js` maps LAMBDA3 JSON-RPC results to outcomes;
   * `runner.js` snapshots each case's ID and source before running and
     compares outcomes;
   * `drafts.js` tracks unsaved edits;
   * `app.js` holds the UI, including the conflict panel, "edited since run"
     flags, and the memory-only warning.
6. Wrote `studio_host.py`, which mounts the page, the database service, and
   the unchanged Assign07 LAMBDA3 app on one origin, and `run.py`.
7. Wrote the HTTP API tests, the client unit tests, the studio integration
   demo, `README.md`, `TESTING.md`, and this file.

## Suggestions I should review

* Hosting both services in one process for the studio (they remain separate
  WSGI apps). Alternatives would be two processes plus CORS, or a proxy.
* The chosen limits (256 KiB body, 64 KiB source, 1,000 programs, 200
  collections, 200 cases, page size 100) and the 10-minute cursor lifetime.
* Body validation errors (`400`) take priority over a stale `If-Match`
  (`409`) when both apply.
* Names are unique case-sensitively, after trimming.
* PUT replaces all editable fields, so an omitted description becomes `""`.

## How the result was reviewed and tested

* I asked the agent to run sanity checks and its own test suites. It reran
  the Python and Node tests, exercised the API with curl against a live
  server, and walked through every studio workflow in a browser on a
  separate test server. All of them passed.
* I then ran the tests myself from `assigns/09` with the commands in
  `README.md`, started the studio, and tried the API and the studio by hand.
* 52 Python tests (50 HTTP-level API tests and 2 integration tests) and 12
  Node client tests pass from `assigns/09` with the README commands. Every
  API response is validated against `openapi.json`.
* The first test run found a real bug: an injected, empty `SnapshotTable`
  was treated as falsy (`snapshots or …`), so the default table silently
  replaced it. It was fixed with an explicit `is not None` check.
* The integration test runs the studio's own JS modules against a real
  server with the real Assign07 LAMBDA3 service. Results: expected value
  `720`, expected syntax error, and expected type error all pass; a wrong
  expectation and a runtime error expecting a syntax error fail; a stale save
  gets `409`.
* Drove the studio in a browser through all five required workflows. That
  covered creating and saving, a stale-revision conflict with reload, case
  add/edit/delete/reload, a collection run with pass/fail summary, the
  network-error banner, reload persistence, and data being cleared after a
  service restart. The results are recorded in `TESTING.md`.
