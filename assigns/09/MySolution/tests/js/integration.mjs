// Studio-level integration demo, run against a REAL server:
//   node tests/js/integration.mjs http://127.0.0.1:8009
// (tests/test_integration.py starts the server and runs this for you.)
//
// It uses the studio's own modules (storage.js, lambda.js, runner.js) and the
// real LAMBDA3 service, so nothing is mocked. It prints one JSON report and
// exits non-zero if any step does not behave as the assignment requires.

import assert from "node:assert/strict";
import { ApiError, createStorage } from "../../web/storage.js";
import { createLambdaClient } from "../../web/lambda.js";
import { describeOutcome, runCollection } from "../../web/runner.js";

const base = process.argv[2] ?? "http://127.0.0.1:8009";
const tag = Date.now().toString(36);  // unique names, in case the server is shared
const FACT = (n) => `let fact = fix f(n: sint): sint => if n <= 0 then 1 else n * f(n - 1) in fact(${n}) end`;
const report = { steps: [] };
const step = (name, detail) => { report.steps.push({ step: name, ...detail }); };

const session1 = createStorage({ baseUrl: `${base}/api/v1` });
const lambda = createLambdaClient({ url: `${base}/lambda/rpc` });

// 1. Both services are reachable.
assert.deepEqual(await session1.health(), { status: "ok", version: "1.0" });
assert.equal(await lambda.health(), true);
step("health", { database: "ok", lambda3: "ok" });

// 2. Save a program, then reload it in a "later browser session" (a new adapter).
const created = await session1.createProgram({ name: `factorial ${tag}`, source: FACT(6), description: "6!" });
const session2 = createStorage({ baseUrl: `${base}/api/v1` });
let listed = [];
for (let cursor; ;) {
  const page = await session2.listPrograms({ limit: 50, cursor });
  listed = listed.concat(page.items);
  if (!page.nextCursor) break;
  cursor = page.nextCursor;
}
assert.ok(listed.some((p) => p.id === created.id));
const reloaded = await session2.getProgram(created.id);
assert.equal(reloaded.source, FACT(6));
assert.equal(reloaded.revision, 1);
step("save and reload program", { id: created.id, revision: reloaded.revision });

// 3. Edit + save, then a stale save from the old copy is refused, not applied.
const edited = await session2.updateProgram(created.id, reloaded.revision, { ...reloaded, source: FACT(5) });
assert.equal(edited.revision, 2);
let conflict = null;
try {
  await session1.updateProgram(created.id, created.revision, { ...created, source: "0" });
} catch (err) {
  conflict = err;
}
assert.ok(conflict instanceof ApiError && conflict.isConflict && conflict.currentRevision === 2);
assert.equal((await session1.getProgram(created.id)).source, FACT(5));  // newer copy kept
step("stale save refused", { status: conflict.status, code: conflict.code, current_revision: conflict.currentRevision });

// 4. Create a collection and add cases (source snapshots, not program links).
let col = await session1.createCollection({ name: `demo ${tag}`, description: "integration demo" });
const cases = [
  { name: "six factorial", source: FACT(6), expected: { kind: "value", value: "720" } },
  { name: "missing operand", source: "1 +", expected: { kind: "error", category: "syntax" } },
  { name: "int plus bool", source: "1 + true", expected: { kind: "error", category: "type" } },
  { name: "wrong expectation", source: FACT(3), expected: { kind: "value", value: "999" } },
  { name: "runtime error is not a syntax error", source: "1 / 0", expected: { kind: "error", category: "syntax" } },
];
for (const c of cases) col = await session1.addCase(col.id, col.revision, c);
// Edit one case and delete nothing; then reload the collection from the service.
const wrong = col.cases[3];
col = await session1.updateCase(col.id, wrong.id, col.revision, { ...wrong, description: "fails on purpose" });
const fresh = await session2.getCollection(col.id);
assert.deepEqual(fresh.cases.map((c) => c.name), cases.map((c) => c.name));
assert.equal(fresh.revision, 1 + cases.length + 1);
step("collection created and reloaded", { id: fresh.id, revision: fresh.revision, cases: fresh.cases.length });

// Deleting the program does not change the stored snapshot.
await session1.deleteProgram(created.id, 2);
assert.equal((await session2.getCollection(col.id)).cases[0].source, FACT(6));

// 5. Run the collection through the real LAMBDA3 service.
const run = await runCollection(fresh, lambda);
const results = run.results.map((r) => ({
  case: r.name, case_id: r.caseId, pass: r.pass, outcome: describeOutcome(r.outcome),
}));
assert.deepEqual(run.results.map((r) => r.pass), [true, true, true, false, false]);
assert.equal(run.results[0].outcome.value, "720");
assert.equal(run.results[1].outcome.status, "syntax_error");
assert.equal(run.results[2].outcome.status, "type_error");
assert.equal(run.results[4].outcome.status, "runtime_error");
step("run collection", { passed: run.passed, failed: run.failed, results });

// 6. Clean up what this demo created.
await session1.deleteCollection(col.id, fresh.revision);
step("cleanup", { deleted: [col.id] });

report.ok = true;
console.log(JSON.stringify(report, null, 2));
