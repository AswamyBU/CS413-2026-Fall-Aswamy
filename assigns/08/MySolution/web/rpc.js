// Transport: a minimal JSON-RPC 2.0 client over fetch. No DOM, no rendering.

export class RpcError extends Error {
  constructor(code, message, data) {
    super(message);
    this.name = "RpcError";
    this.code = code;
    this.data = data;
  }
}

export class TransportError extends Error {
  constructor(message) {
    super(message);
    this.name = "TransportError";
  }
}

export const STREAM_NOT_FOUND = -32001;

export function createRpcClient({ url = "/rpc", fetchImpl = (...a) => globalThis.fetch(...a) } = {}) {
  let nextId = 1;

  async function call(method, params = {}) {
    const id = nextId++;
    let response;
    try {
      response = await fetchImpl(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", method, params, id }),
      });
    } catch (err) {
      throw new TransportError(`Network error: ${err && err.message ? err.message : err}`);
    }
    if (!response.ok) {
      throw new TransportError(`HTTP ${response.status} from ${url}`);
    }
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new TransportError("Server sent a response that is not JSON");
    }
    if (payload.error) {
      throw new RpcError(payload.error.code, payload.error.message, payload.error.data);
    }
    if (payload.id !== id || !("result" in payload)) {
      throw new TransportError("Malformed JSON-RPC response");
    }
    return payload.result;
  }

  return {
    call,
    health: () => call("service.health", {}),
    open: (size) => call("queens.open", { size }),
    next: (streamId, limit) => call("queens.next", { stream_id: streamId, limit }),
    close: (streamId) => call("queens.close", { stream_id: streamId }),
  };
}
