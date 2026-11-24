// Collection runner and outcome comparison. No DOM, no REST: it receives a
// collection record and a LAMBDA3 client.

// Does a LAMBDA3 outcome satisfy a stored expectation? (API.md section 10)
export function compareOutcome(expected, outcome) {
  if (expected.kind === "value") {
    if (outcome.status !== "value") return { pass: false, reason: `expected value ${expected.value}, got ${describeOutcome(outcome)}` };
    if (outcome.value !== expected.value) return { pass: false, reason: `expected ${expected.value}, got ${outcome.value}` };
    return { pass: true, reason: `value ${outcome.value}` };
  }
  const wanted = expected.category === "syntax" ? "syntax_error" : "type_error";
  if (outcome.status === wanted) return { pass: true, reason: `${expected.category} error as expected` };
  return { pass: false, reason: `expected a ${expected.category} error, got ${describeOutcome(outcome)}` };
}

export function describeOutcome(outcome) {
  switch (outcome.status) {
    case "value": return `value ${outcome.value}`;
    case "syntax_error": return "a syntax error";
    case "type_error": return "a type error";
    case "timeout": return "a timeout";
    case "runtime_error": return "a runtime error";
    case "service_error": return `a service error (${outcome.code})`;
    default: return `a transport failure (${outcome.message})`;
  }
}

export function describeExpected(expected) {
  return expected.kind === "value" ? `value ${expected.value}` : `${expected.category} error`;
}

// Run every case of `collection` through `lambda.interpret`, in order.
// The cases are copied up front, so each result carries the exact case ID and
// source snapshot that produced it, even if the collection is edited while the
// run is in progress. One failing case never stops the others.
export async function runCollection(collection, lambda, { onResult = () => {}, shouldStop = () => false } = {}) {
  const snapshot = collection.cases.map((c) => Object.freeze({
    caseId: c.id, name: c.name, source: c.source, expected: { ...c.expected },
  }));
  const run = {
    collectionId: collection.id,
    revision: collection.revision,
    results: [],
    passed: 0,
    failed: 0,
    stopped: false,
  };
  for (const item of snapshot) {
    if (shouldStop()) { run.stopped = true; break; }
    let outcome;
    try {
      outcome = await lambda.interpret(item.source);
    } catch (err) {
      outcome = { status: "transport_error", message: err?.message ?? String(err) };
    }
    const verdict = compareOutcome(item.expected, outcome);
    const result = Object.freeze({ ...item, outcome, pass: verdict.pass, reason: verdict.reason });
    run.results.push(result);
    if (result.pass) run.passed += 1; else run.failed += 1;
    onResult(result, run);
  }
  return run;
}

// Has a case changed since a result was produced? Used to flag stale results.
export function resultIsStale(result, collection) {
  const current = collection?.cases.find((c) => c.id === result.caseId);
  if (!current) return "deleted";
  if (current.source !== result.source
      || JSON.stringify(current.expected) !== JSON.stringify(result.expected)) return "edited";
  return null;
}
