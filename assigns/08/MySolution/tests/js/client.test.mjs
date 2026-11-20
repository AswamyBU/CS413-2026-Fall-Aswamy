// Client tests (Node's built-in runner, no packages): node --test tests/js/
// The DOM layer (main.js) is covered by the browser checklist in TESTING.md;
// everything it delegates to is tested here with fake transports and timers.

import { test } from "node:test";
import assert from "node:assert/strict";

import { applyEvent, attackers, cellState, describeEvent, initialView } from "../../web/board.js";
import { FAST_BATCH, PLAY_BATCH, Player } from "../../web/player.js";
import { RpcError, TransportError, createRpcClient } from "../../web/rpc.js";

// ---------------------------------------------------------------- fakes

// Replays a scripted 4x4 trace in the shape queens.next returns, and records
// every call so tests can check that events are requested incrementally.
function fakeServer(trace, { failOn = null } = {}) {
  const calls = [];
  let cursor = 0;
  let open = false;
  return {
    calls,
    get cursor() { return cursor; },
    async open(size) {
      calls.push(["open", size]);
      if (failOn === "open") throw new TransportError("Network error: offline");
      open = true; cursor = 0;
      return { stream_id: "s-1", size };
    },
    async next(id, limit) {
      calls.push(["next", id, limit]);
      if (failOn === "next") throw new RpcError(-32001, "Stream not found");
      assert.ok(open, "next before open");
      const events = trace.slice(cursor, cursor + limit);
      cursor += events.length;
      return { events, done: cursor >= trace.length };
    },
    async close(id) { calls.push(["close", id]); open = false; return { closed: true }; },
  };
}

function manualTimers() {
  const queue = [];
  return {
    schedule: (fn, ms) => { queue.push({ fn, ms }); return queue.length; },
    cancel: () => { queue.length = 0; },
    pending: () => queue.length,
    async fire() { const t = queue.shift(); if (t) await t.fn(); },
  };
}

const T = (event, column, row, board) => ({ event, column, row, board });
// First steps of the real 4x4 trace, then a solution, then done.
const TRACE = [
  T("try", 0, 0, []), T("place", 0, 0, [0]),
  T("try", 0, 1, [0]), T("reject", 0, 1, [0]),
  T("try", 1, 1, [0]), T("reject", 1, 1, [0]),
  T("try", 2, 1, [0]), T("place", 2, 1, [0, 2]),
  T("try", 0, 2, [0, 2]), T("reject", 0, 2, [0, 2]),
  T("backtrack", 2, 1, [0]),
  T("try", 1, 0, []), T("place", 1, 0, [1]),
  { event: "solution", board: [1, 3, 0, 2], number: 1 },
  T("backtrack", 2, 3, [1, 3, 0]),
  { event: "solution", board: [2, 0, 3, 1], number: 2 },
  T("backtrack", 3, 0, []),
  { event: "done" },
];

const flush = () => new Promise((r) => setImmediate(r));

// ---------------------------------------------------------------- board.js

test("reducer: try, place, reject, backtrack, solution, done", () => {
  let v = initialView(4);
  v = applyEvent(v, TRACE[0]);
  assert.deepEqual(v.cursor, { row: 0, column: 0, kind: "try" });
  assert.deepEqual(cellState(v, 0, 0), { queen: false, state: "try" });
  v = applyEvent(v, TRACE[1]);
  assert.deepEqual(v.board, [0]);
  assert.deepEqual(cellState(v, 0, 0), { queen: true, state: "place" });
  v = applyEvent(applyEvent(v, TRACE[2]), TRACE[3]);
  assert.deepEqual(cellState(v, 1, 0), { queen: false, state: "reject" });
  assert.deepEqual(cellState(v, 0, 0), { queen: true, state: "conflict" });
  assert.deepEqual(v.conflicts, [0]);
  v = applyEvent(v, TRACE[10]);
  assert.deepEqual(v.board, [0]);
  assert.deepEqual(cellState(v, 1, 2), { queen: false, state: "backtrack" });
  v = applyEvent(v, TRACE[13]);
  assert.equal(v.solutions, 1);
  assert.deepEqual(cellState(v, 3, 2), { queen: true, state: "solution" });
  v = applyEvent(v, TRACE[17]);
  assert.equal(v.done, true);
  assert.equal(v.solutions, 1);
  assert.deepEqual(v.stats, { try: 2, place: 1, reject: 1, backtrack: 1 });
  assert.equal(v.events, 7);
});

test("reducer is pure and rejects unknown events", () => {
  const v0 = initialView(8);
  const v1 = applyEvent(v0, TRACE[1]);
  assert.deepEqual(v0.board, []);
  assert.notEqual(v0, v1);
  assert.throws(() => applyEvent(v0, { event: "bogus" }));
});

test("attackers finds same-column and both diagonals", () => {
  assert.deepEqual(attackers([0, 2], 2, 0), [0]);     // same column
  assert.deepEqual(attackers([0, 2], 2, 1), [1]);     // diagonal from upper right
  assert.deepEqual(attackers([3, 4], 2, 1), [0]);     // diagonal from upper right, distance 2
  assert.deepEqual(attackers([3, 0], 2, 1), [0, 1]);  // two attackers at once
  assert.deepEqual(attackers([1, 3], 2, 2), [1]);     // diagonal from upper left
  assert.deepEqual(attackers([1, 3], 2, 0), []);      // safe
});

test("describeEvent distinguishes a solution from completion", () => {
  assert.match(describeEvent(TRACE[13]), /^SOLUTION #1/);
  assert.match(describeEvent({ event: "done" }), /search complete/);
});

// ---------------------------------------------------------------- player.js

test("start opens a stream but fetches no events", async () => {
  const server = fakeServer(TRACE);
  const p = new Player({ rpc: server, size: 4 });
  await p.start();
  assert.equal(p.state, "ready");
  assert.deepEqual(server.calls, [["open", 4]]);
  assert.equal(p.view.events, 0);
});

test("step requests one small batch and consumes the buffer before asking again", async () => {
  const server = fakeServer(TRACE);
  const p = new Player({ rpc: server, size: 4 });
  await p.start();
  await p.step();
  assert.deepEqual(server.calls.at(-1), ["next", "s-1", PLAY_BATCH]);
  assert.equal(server.cursor, PLAY_BATCH);
  for (let i = 1; i < PLAY_BATCH; i++) await p.step();
  assert.equal(server.calls.filter((c) => c[0] === "next").length, 1);
  assert.equal(p.view.events, PLAY_BATCH);
  await p.step();
  assert.equal(server.calls.filter((c) => c[0] === "next").length, 2);
});

test("play/pause advance one event per timer tick", async () => {
  const server = fakeServer(TRACE);
  const timers = manualTimers();
  const p = new Player({ rpc: server, size: 4, delay: 50, ...timers });
  await p.start();
  p.play();
  assert.equal(p.state, "playing");
  await timers.fire();
  await timers.fire();
  await timers.fire();
  assert.equal(p.view.events, 3);
  p.pause();
  assert.equal(p.state, "ready");
  assert.equal(timers.pending(), 0);
  await timers.fire();
  assert.equal(p.view.events, 3);
  p.toggle();
  assert.equal(p.state, "playing");
});

test("play runs to completion and stops at done", async () => {
  const server = fakeServer(TRACE);
  const timers = manualTimers();
  const p = new Player({ rpc: server, size: 4, ...timers });
  await p.start();
  p.play();
  while (timers.pending()) await timers.fire();
  assert.equal(p.state, "complete");
  assert.equal(p.view.solutions, 2);
  assert.equal(p.view.done, true);
  assert.equal(await p.step(), null);  // nothing after done
});

test("next solution stops on the solution event, then on done", async () => {
  const server = fakeServer(TRACE);
  const p = new Player({ rpc: server, size: 4 });
  await p.start();
  const first = await p.nextSolution();
  assert.equal(first.event, "solution");
  assert.equal(p.view.solutions, 1);
  assert.equal(p.state, "ready");
  assert.deepEqual(server.calls[1], ["next", "s-1", FAST_BATCH]);
  assert.equal((await p.nextSolution()).number, 2);
  const last = await p.nextSolution();
  assert.equal(last.event, "done");
  assert.equal(p.state, "complete");
});

test("reset closes the stream and clears the board; start after done restarts", async () => {
  const server = fakeServer(TRACE);
  const p = new Player({ rpc: server, size: 4 });
  await p.start();
  await p.step();
  await p.reset();
  assert.deepEqual(server.calls.at(-1), ["close", "s-1"]);
  assert.equal(p.state, "idle");
  assert.equal(p.view.events, 0);
  await p.start();
  while (p.state !== "complete") await p.nextSolution();
  await p.start();  // restart after completion
  assert.equal(p.state, "ready");
  assert.equal(p.view.solutions, 0);
});

test("RPC failures are reported and stop playback", async () => {
  const errors = [];
  const p = new Player({ rpc: fakeServer(TRACE, { failOn: "next" }), size: 4, onError: (e) => errors.push(e) });
  await p.start();
  await p.step();
  assert.equal(p.state, "error");
  assert.equal(errors[0].code, -32001);

  const q = new Player({ rpc: fakeServer(TRACE, { failOn: "open" }), size: 4, onError: (e) => errors.push(e) });
  await q.start();
  assert.equal(q.state, "error");
  assert.ok(errors[1] instanceof TransportError);
});

test("buttons are no-ops before start", async () => {
  const server = fakeServer(TRACE);
  const p = new Player({ rpc: server, size: 4 });
  assert.equal(await p.step(), null);
  p.play();
  assert.equal(await p.nextSolution(), null);
  assert.equal(server.calls.length, 0);
});

// ---------------------------------------------------------------- rpc.js

function fakeFetch(handler) {
  const requests = [];
  const fn = async (url, init) => {
    requests.push({ url, body: JSON.parse(init.body), headers: init.headers });
    return handler(requests.at(-1));
  };
  fn.requests = requests;
  return fn;
}
const jsonResponse = (payload, status = 200) => ({ ok: status < 400, status, json: async () => payload });

test("rpc client sends JSON-RPC 2.0 with increasing ids", async () => {
  const fetchImpl = fakeFetch(({ body }) => jsonResponse({ jsonrpc: "2.0", id: body.id, result: { ok: body.method } }));
  const rpc = createRpcClient({ fetchImpl });
  assert.deepEqual(await rpc.open(8), { ok: "queens.open" });
  await rpc.next("abc", 4);
  assert.deepEqual(fetchImpl.requests[1].body, {
    jsonrpc: "2.0", method: "queens.next", params: { stream_id: "abc", limit: 4 }, id: 2,
  });
  assert.equal(fetchImpl.requests[0].headers["Content-Type"], "application/json");
  assert.equal(fetchImpl.requests[0].url, "/rpc");
});

test("rpc client surfaces JSON-RPC errors, HTTP errors and network failures", async () => {
  const errorFetch = fakeFetch(({ body }) =>
    jsonResponse({ jsonrpc: "2.0", id: body.id, error: { code: -32602, message: "Invalid params" } }));
  await assert.rejects(createRpcClient({ fetchImpl: errorFetch }).open(99),
    (e) => e instanceof RpcError && e.code === -32602);

  const httpFetch = fakeFetch(() => jsonResponse(null, 500));
  await assert.rejects(createRpcClient({ fetchImpl: httpFetch }).health(), TransportError);

  const offline = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(createRpcClient({ fetchImpl: offline }).health(), /Network error/);
});

await flush();
