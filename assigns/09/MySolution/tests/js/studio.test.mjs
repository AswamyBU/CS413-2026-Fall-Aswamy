// Unit tests for the studio client modules (Node built-in runner, no packages):
//   node --test "tests/js/*.test.mjs"
// Fakes stand in for fetch only; the modules under test are the real ones.

import { test } from "node:test";
import assert from "node:assert/strict";

import { ApiError, NetworkError, createStorage } from "../../web/storage.js";
import { createLambdaClient } from "../../web/lambda.js";
import { compareOutcome, resultIsStale, runCollection } from "../../web/runner.js";
import { caseDraft, caseFromDraft, isDirty, programDraft } from "../../web/drafts.js";

function fakeFetch(handler) {
  const calls = [];
  const fn = async (url, init = {}) => {
    const call = { url, method: init.method, headers: init.headers ?? {}, body: init.body ? JSON.parse(init.body) : undefined };
    calls.push(call);
    return handler(call);
  };
  fn.calls = calls;
  return fn;
}
const reply = (status, payload) => ({ ok: status < 400, status, json: async () => payload });

// ---------------------------------------------------------------- storage adapter

test("adapter: create sends JSON, no If-Match; returns the record", async () => {
  const fetchImpl = fakeFetch(() => reply(201, { program: { id: "prg_1", revision: 1 } }));
  const s = createStorage({ fetchImpl });
  const p = await s.createProgram({ name: "f", source: "1" });
  assert.deepEqual(p, { id: "prg_1", revision: 1 });
  const call = fetchImpl.calls[0];
  assert.equal(call.url, "/api/v1/programs");
  assert.equal(call.method, "POST");
  assert.equal(call.headers["Content-Type"], "application/json");
  assert.equal(call.headers["If-Match"], undefined);
  assert.deepEqual(call.body, { name: "f", source: "1", description: "" });
});

test("adapter: updates and deletes send the revision as a quoted If-Match", async () => {
  const fetchImpl = fakeFetch((c) => c.method === "DELETE" && !c.url.includes("/cases/")
    ? reply(204, null) : reply(200, { program: { revision: 4 }, collection: { revision: 9 } }));
  const s = createStorage({ fetchImpl });
  await s.updateProgram("prg_1", 3, { name: "f", source: "1" });
  assert.equal(await s.deleteProgram("prg_1", 4), null);
  await s.addCase("col_1", 7, { name: "c", source: "1", expected: { kind: "value", value: "1" } });
  await s.updateCase("col_1", "case_1", 8, { name: "c", source: "1", expected: { kind: "error", category: "type" } });
  await s.deleteCase("col_1", "case_1", 9);
  assert.deepEqual(fetchImpl.calls.map((c) => [c.method, c.url, c.headers["If-Match"]]), [
    ["PUT", "/api/v1/programs/prg_1", '"3"'],
    ["DELETE", "/api/v1/programs/prg_1", '"4"'],
    ["POST", "/api/v1/collections/col_1/cases", '"7"'],
    ["PUT", "/api/v1/collections/col_1/cases/case_1", '"8"'],
    ["DELETE", "/api/v1/collections/col_1/cases/case_1", '"9"'],
  ]);
});

test("adapter: list builds the query and maps next_cursor", async () => {
  const fetchImpl = fakeFetch(() => reply(200, { items: [{ id: "a" }], next_cursor: "tok" }));
  const page = await createStorage({ fetchImpl }).listCollections({ limit: 20, cursor: "abc" });
  assert.deepEqual(page, { items: [{ id: "a" }], nextCursor: "tok" });
  assert.equal(fetchImpl.calls[0].url, "/api/v1/collections?limit=20&cursor=abc");
});

test("adapter: API errors become ApiError with code and details", async () => {
  const fetchImpl = fakeFetch(() => reply(409, { error: { code: "revision_conflict", message: "stale", current_revision: 5 } }));
  await assert.rejects(createStorage({ fetchImpl }).updateProgram("prg_1", 4, { name: "f", source: "1" }), (e) => {
    assert.ok(e instanceof ApiError);
    assert.equal(e.status, 409);
    assert.ok(e.isConflict);
    assert.equal(e.currentRevision, 5);
    return true;
  });
  const bad = fakeFetch(() => reply(400, { error: { code: "invalid_request", message: "name must not be blank", field: "name" } }));
  await assert.rejects(createStorage({ fetchImpl: bad }).createProgram({ name: " ", source: "1" }),
    (e) => e.code === "invalid_request" && e.details.field === "name" && !e.isConflict);
});

test("adapter: network failures become NetworkError", async () => {
  const s = createStorage({ fetchImpl: async () => { throw new TypeError("Failed to fetch"); } });
  await assert.rejects(s.health(), NetworkError);
  const html = createStorage({ fetchImpl: async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError(); } }) });
  await assert.rejects(html.health(), NetworkError);
});

// ---------------------------------------------------------------- LAMBDA3 client

function lambdaWith(respond) {
  return createLambdaClient({
    fetchImpl: fakeFetch((c) => respond(c)),
  });
}

test("lambda client: success and error codes map to outcome statuses", async () => {
  const ok = lambdaWith((c) => reply(200, { jsonrpc: "2.0", id: c.body.id, result: { value: "720", type: "sint" } }));
  assert.deepEqual(await ok.interpret("x"), { status: "value", value: "720", type: "sint" });
  for (const [code, status] of [[-32010, "syntax_error"], [-32011, "type_error"], [-32012, "timeout"],
    [-32013, "runtime_error"], [-32014, "service_error"], [-32603, "service_error"]]) {
    const client = lambdaWith((c) => reply(200, { jsonrpc: "2.0", id: c.body.id, error: { code, message: "m" } }));
    assert.equal((await client.interpret("x")).status, status, String(code));
  }
});

test("lambda client: sends lambda.interpret and reports transport failures", async () => {
  const fetchImpl = fakeFetch((c) => reply(200, { jsonrpc: "2.0", id: c.body.id, result: { value: "1", type: "sint" } }));
  await createLambdaClient({ fetchImpl }).interpret("1");
  assert.deepEqual(fetchImpl.calls[0].body, { jsonrpc: "2.0", method: "lambda.interpret", params: { source: "1" }, id: 1 });
  assert.equal(fetchImpl.calls[0].url, "/lambda/rpc");
  const down = createLambdaClient({ fetchImpl: async () => { throw new TypeError("offline"); } });
  assert.equal((await down.interpret("1")).status, "transport_error");
  assert.equal((await lambdaWith(() => reply(500, null)).interpret("1")).status, "transport_error");
  assert.equal((await lambdaWith(() => reply(200, { jsonrpc: "2.0", id: 999, result: {} })).interpret("1")).status, "transport_error");
});

// ---------------------------------------------------------------- comparison

test("compare: value expectations need success and an exactly equal value", () => {
  const e = { kind: "value", value: "720" };
  assert.equal(compareOutcome(e, { status: "value", value: "720" }).pass, true);
  assert.equal(compareOutcome(e, { status: "value", value: "720 " }).pass, false);
  assert.equal(compareOutcome(e, { status: "value", value: "120" }).pass, false);
  assert.equal(compareOutcome(e, { status: "syntax_error" }).pass, false);
});

test("compare: error expectations match only their own category", () => {
  const syntax = { kind: "error", category: "syntax" };
  const type = { kind: "error", category: "type" };
  assert.equal(compareOutcome(syntax, { status: "syntax_error" }).pass, true);
  assert.equal(compareOutcome(type, { status: "type_error" }).pass, true);
  assert.equal(compareOutcome(syntax, { status: "type_error" }).pass, false);
  assert.equal(compareOutcome(type, { status: "syntax_error" }).pass, false);
  for (const status of ["timeout", "runtime_error", "service_error", "transport_error", "value"]) {
    assert.equal(compareOutcome(syntax, { status, message: "x", value: "1" }).pass, false, status);
    assert.equal(compareOutcome(type, { status, message: "x", value: "1" }).pass, false, status);
  }
});

// ---------------------------------------------------------------- runner

const collection = () => ({
  id: "col_1", revision: 4,
  cases: [
    { id: "case_a", name: "ok", source: "A", expected: { kind: "value", value: "1" }, description: "" },
    { id: "case_b", name: "boom", source: "B", expected: { kind: "value", value: "2" }, description: "" },
    { id: "case_c", name: "syntax", source: "C", expected: { kind: "error", category: "syntax" }, description: "" },
    { id: "case_d", name: "down", source: "D", expected: { kind: "value", value: "4" }, description: "" },
  ],
});

test("runner: one failure does not stop the remaining cases", async () => {
  const lambda = {
    async interpret(src) {
      if (src === "A") return { status: "value", value: "1" };
      if (src === "B") throw new Error("socket hang up");
      if (src === "C") return { status: "syntax_error" };
      return { status: "transport_error", message: "offline" };
    },
  };
  const seen = [];
  const run = await runCollection(collection(), lambda, { onResult: (r) => seen.push(r.caseId) });
  assert.deepEqual(seen, ["case_a", "case_b", "case_c", "case_d"]);
  assert.deepEqual(run.results.map((r) => r.pass), [true, false, true, false]);
  assert.equal(run.passed, 2);
  assert.equal(run.failed, 2);
  assert.equal(run.results[1].outcome.status, "transport_error");
  assert.equal(run.revision, 4);
});

test("runner: results keep the case ID and source snapshot even if the collection is edited mid-run", async () => {
  const c = collection();
  const lambda = {
    async interpret(src) {
      // While case A runs, the user edits case A and deletes case B.
      if (src === "A") { c.cases[0].source = "EDITED"; c.cases[0].name = "renamed"; c.cases.splice(1, 1); }
      return { status: "value", value: src === "A" ? "1" : "x" };
    },
  };
  const run = await runCollection(c, lambda);
  assert.equal(run.results.length, 4);  // the snapshot taken at start is what runs
  assert.deepEqual(run.results.map((r) => [r.caseId, r.source]),
    [["case_a", "A"], ["case_b", "B"], ["case_c", "C"], ["case_d", "D"]]);
  assert.equal(run.results[0].name, "ok");
  assert.equal(resultIsStale(run.results[0], c), "edited");
  assert.equal(resultIsStale(run.results[1], c), "deleted");
  assert.equal(resultIsStale(run.results[2], c), null);
  assert.throws(() => { run.results[0].source = "x"; });  // frozen
});

// ---------------------------------------------------------------- drafts

test("drafts: dirty tracking and case conversion", () => {
  const base = programDraft({ name: "f", description: "", source: "1" });
  assert.equal(isDirty({ ...base }, base), false);
  assert.equal(isDirty({ ...base, source: "2" }, base), true);
  assert.equal(isDirty(programDraft(null), programDraft(null)), false);
  const d = caseDraft({ name: "c", source: "1 +", description: "", expected: { kind: "error", category: "syntax" } });
  assert.deepEqual(caseFromDraft(d), { name: "c", source: "1 +", description: "", expected: { kind: "error", category: "syntax" } });
  assert.deepEqual(caseFromDraft({ ...d, kind: "value", value: "3" }).expected, { kind: "value", value: "3" });
});
