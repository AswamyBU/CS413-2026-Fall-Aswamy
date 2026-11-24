// Client for the LAMBDA3 JSON-RPC service from Assign07. It turns every
// response, error, or failure into one plain "outcome" object, so the runner
// never sees HTTP or JSON-RPC details.
//
// outcome.status is one of:
//   "value"         interpretation succeeded: { value, type }
//   "syntax_error"  JSON-RPC -32010
//   "type_error"    JSON-RPC -32011
//   "timeout"       JSON-RPC -32012
//   "runtime_error" JSON-RPC -32013
//   "service_error" any other JSON-RPC error (limits, internal, ...)
//   "transport_error" network failure, HTTP error, or malformed response

const STATUS_BY_CODE = {
  [-32010]: "syntax_error",
  [-32011]: "type_error",
  [-32012]: "timeout",
  [-32013]: "runtime_error",
};

export function createLambdaClient({ url = "/lambda/rpc", fetchImpl = (...a) => globalThis.fetch(...a) } = {}) {
  let nextId = 1;

  async function call(method, params) {
    const id = nextId++;
    let response;
    try {
      response = await fetchImpl(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", method, params, id }),
      });
    } catch (err) {
      return { status: "transport_error", message: `Cannot reach LAMBDA3 (${err?.message ?? err})` };
    }
    if (!response.ok) return { status: "transport_error", message: `LAMBDA3 returned HTTP ${response.status}` };
    let payload;
    try {
      payload = await response.json();
    } catch {
      return { status: "transport_error", message: "LAMBDA3 sent a non-JSON response" };
    }
    if (payload?.id !== id) return { status: "transport_error", message: "Malformed JSON-RPC response" };
    if (payload.error) {
      return {
        status: STATUS_BY_CODE[payload.error.code] ?? "service_error",
        code: payload.error.code,
        message: payload.error.message,
      };
    }
    return { status: "ok", result: payload.result };
  }

  return {
    async health() {
      const r = await call("service.health", {});
      return r.status === "ok";
    },
    async interpret(source) {
      const r = await call("lambda.interpret", { source });
      if (r.status !== "ok") return r;
      return { status: "value", value: r.result.value, type: r.result.type };
    },
  };
}
