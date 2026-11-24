# Assign09: In-Memory Database Service for LAMBDA-studio

A REST service that stores LAMBDA **programs** and **test collections** in
process memory, plus a small **LAMBDA Studio** web client that saves, edits,
and reloads programs, manages test cases, and runs collections through the
LAMBDA3 JSON-RPC service from Assign07.

> **Data lives only in memory.** Records survive browser reloads and new
> browser sessions while the service runs, and are **cleared when the
> service process stops**. The studio shows this warning at the top of every
> page. There is no file, SQLite, or browser-storage persistence.

The full contract is in [API.md](API.md) and [openapi.json](openapi.json)
(OpenAPI 3.1). The requirement-to-test map is in [TESTING.md](TESTING.md).

## Architecture

```text
 Browser: LAMBDA Studio (web/)
┌──────────────────────────────────────────────────────────────┐
│ app.js       DOM, forms, unsaved-edit badges, conflict panel │
│   │                    │                     │               │
│ drafts.js    runner.js (snapshot cases, run, compare)        │
│   │                    │                                     │
│ storage.js  ◄── storage adapter: the ONLY place that knows   │
│   │              REST routes, ETag/If-Match, error envelope  │
│   │          lambda.js  ◄── LAMBDA3 JSON-RPC client          │
└───┼────────────────────┼─────────────────────────────────────┘
    │ REST /api/v1/...   │ JSON-RPC POST /lambda/rpc
    ▼                    ▼
┌──────────────────────────────┐   ┌─────────────────────────────┐
│ Database service (studio_db) │   │ LAMBDA3 service (Assign07,  │
│  api.py        HTTP routes   │   │ imported unchanged)         │
│  validation.py request rules │   │  lambda.interpret / ...     │
│  service.py    business rules│   │  parse, type-check, run     │
│     │  one lock per mutation │   │  in a worker process        │
│  pagination.py snapshots     │   └─────────────────────────────┘
│  store.py      Store interface        ▲
│     └─ MemoryStore (dicts in RAM)     │ never called by studio_db
└──────────────────────────────┘
        both mounted by studio_host.py on one origin (no CORS)
```

- The **database service never runs LAMBDA code**. It doesn't import
  LAMBDA3; a test checks this in a fresh interpreter.
- The **studio** reads cases from the database and sends each case's stored
  source to LAMBDA3 itself.
- `studio_host.py` mounts the two independent WSGI apps side by side
  (`DispatcherMiddleware`) and serves the page, so the browser needs one URL.

## Versions

| Tool | Version used |
| --- | --- |
| Python | 3.14.0 (3.12+ required) |
| Flask / Werkzeug | 3.1.3 / 3.1.9 |
| jsonschema (tests only) | 4.26.0 |
| Node.js (client tests, integration demo) | 24.11.1 (20+ required) |
| OS tested | Windows 11 |

The LAMBDA3 service comes from `assigns/07/MySolution` (override the location
with the `LAMBDA_RPC_DIR` environment variable). It uses `assigns/07/LAMBDA3`.

## Setup

All commands are run from the **assignment directory** (`assigns/09`).

```bash
python -m venv MySolution/.venv
```

```bash
MySolution/.venv/Scripts/python -m pip install -r MySolution/requirements.txt
```

(On macOS/Linux use `MySolution/.venv/bin/python` instead of
`MySolution/.venv/Scripts/python`.)

## Start

```bash
MySolution/.venv/Scripts/python MySolution/run.py
```

| What | URL |
| --- | --- |
| Studio page | http://127.0.0.1:8009/ |
| Database API (base URL) | http://127.0.0.1:8009/api/v1 |
| LAMBDA3 JSON-RPC (Assign07) | http://127.0.0.1:8009/lambda/rpc |

Options: `--port 8009`, `--host 127.0.0.1`. `--db-only` starts only the
database service and the page; the page then shows LAMBDA3 as unreachable.

## Test

```bash
MySolution/.venv/Scripts/python -m unittest discover -s MySolution/tests -t MySolution -v
```

```bash
node --test "MySolution/tests/js/*.test.mjs"
```

The Python suite includes the studio integration demo. It starts a real
server and runs `tests/js/integration.mjs` with Node against real LAMBDA3.
You can also run the demo by hand against a running studio:

```bash
node MySolution/tests/js/integration.mjs http://127.0.0.1:8009
```

## Using the studio

- **Programs** (left): **New**, then type a name and source, then **Save**. An orange
  **● Unsaved changes** badge appears whenever the form differs from the saved
  revision, and the browser warns before leaving with unsaved edits.
  **Run with LAMBDA3** shows the value or error. **Reload from server**
  re-reads the record. **Add as test case…** copies the current source into a
  collection as a new case.
- **Stale revision:** if someone else saved a newer revision, **Save** is
  refused. A red panel explains that your edits were *not* written, shows
  the server's copy, and offers **Reload server copy** or **Keep my edits**.
  Nothing is overwritten silently.
- **Test collections:** **New**, then **Add case** (name, source snapshot, and
  expected value or syntax/type error). Each case has **Edit** and
  **Delete**; **Reload from server** re-reads the collection.
- **Run collection:** each case runs through LAMBDA3 in order, and one
  failure does not stop the rest. The summary lists PASS/FAIL per case.
  Results are tied to the case ID and source that produced them. If a case
  is edited or deleted afterwards, its result is marked
  *edited/deleted since run*.

## Limits

| Limit | Value |
| --- | --- |
| Request body | 256 KiB (`413`) |
| Name | 100 characters after trimming |
| Source | 65,536 UTF-8 bytes |
| Description | 2,000 characters |
| Expected value | 10,000 characters |
| Page size | `limit` 1–100, default 50 |
| Programs / collections / cases per collection | 1,000 / 200 / 200 (`409 capacity_limit`) |
| List snapshots (cursors) | 256 live, 10-minute idle lifetime, all lost on restart |

## Examples (curl)

```bash
curl -s http://127.0.0.1:8009/api/v1/health
```

```bash
curl -si -X POST http://127.0.0.1:8009/api/v1/programs -H "Content-Type: application/json" -d '{"name": "six", "source": "let fact = fix f(n: sint): sint => if n <= 0 then 1 else n * f(n - 1) in fact(6) end"}'
```

```bash
curl -s "http://127.0.0.1:8009/api/v1/programs?limit=10"
```

```bash
curl -si -X PUT http://127.0.0.1:8009/api/v1/programs/PRG_ID -H "Content-Type: application/json" -H 'If-Match: "1"' -d '{"name": "six", "source": "1 + 2"}'
```

```bash
curl -si -X DELETE http://127.0.0.1:8009/api/v1/programs/PRG_ID -H 'If-Match: "2"'
```

```bash
curl -si -X POST http://127.0.0.1:8009/api/v1/collections -H "Content-Type: application/json" -d '{"name": "basics"}'
```

```bash
curl -si -X POST http://127.0.0.1:8009/api/v1/collections/COL_ID/cases -H "Content-Type: application/json" -H 'If-Match: "1"' -d '{"name": "bad syntax", "source": "1 +", "expected": {"kind": "error", "category": "syntax"}}'
```

A stale `If-Match` returns:

```json
{"error": {"code": "revision_conflict", "message": "If-Match \"1\" does not match the current revision 2", "current_revision": 2}}
```

## Layout

```text
MySolution/
  API.md, openapi.json      contract (written before the routes)
  run.py                    start the studio + both services
  studio_host.py            mounts studio page, studio_db, and Assign07 LAMBDA3
  studio_db/                the database service
    api.py  validation.py  service.py  pagination.py  store.py  records.py  errors.py  config.py
  web/                      LAMBDA Studio: index.html, studio.css, app.js,
                            storage.js (adapter), lambda.js, runner.js, drafts.js
  tests/                    test_api.py (HTTP API), test_integration.py,
                            helpers.py, js/studio.test.mjs, js/integration.mjs
```

## Limitations

- **In-memory only:** everything, including list cursors, is gone when the
  process stops. No export/import is provided.
- Local, single-user, no authentication. It listens on 127.0.0.1 by default.
- Names are unique case-sensitively (`Fact` and `fact` are different).
- One lock serializes all writes. That is ample for one local user, but it
  is not built for heavy concurrent load.
- The studio is a small demonstration client rather than the Assign03
  interface, because Assign03 produced a requirements document and no UI code.
- Test runs are sequential and use LAMBDA3's own 5-second interpretation
  limit; a timeout counts as a failure.
