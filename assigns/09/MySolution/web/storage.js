// Storage adapter: the only module that knows the database service's REST
// routes, HTTP methods, ETag/If-Match headers and error envelope. UI code calls
// plain methods with plain objects and gets records (with `revision`) back.

export class ApiError extends Error {
  constructor(status, code, message, details = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
  get isConflict() { return this.code === "revision_conflict"; }
  get currentRevision() { return this.details.current_revision ?? null; }
}

export class NetworkError extends Error {
  constructor(message) {
    super(message);
    this.name = "NetworkError";
  }
}

const etag = (revision) => `"${revision}"`;

export function createStorage({ baseUrl = "/api/v1", fetchImpl = (...a) => globalThis.fetch(...a) } = {}) {
  async function request(method, path, { body, revision } = {}) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (revision !== undefined) headers["If-Match"] = etag(revision);
    let response;
    try {
      response = await fetchImpl(baseUrl + path, {
        method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (err) {
      throw new NetworkError(`Cannot reach the database service (${err?.message ?? err})`);
    }
    if (response.status === 204) return null;
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      if (response.ok) throw new NetworkError("Database service sent a non-JSON response");
    }
    if (!response.ok) {
      const e = payload?.error ?? {};
      const { code = "http_error", message = `HTTP ${response.status}`, ...details } = e;
      throw new ApiError(response.status, code, message, details);
    }
    return payload;
  }

  const q = (params) => {
    const s = new URLSearchParams();
    if (params.limit !== undefined) s.set("limit", String(params.limit));
    if (params.cursor) s.set("cursor", params.cursor);
    const text = s.toString();
    return text ? `?${text}` : "";
  };
  const page = (p) => ({ items: p.items, nextCursor: p.next_cursor });
  const id = encodeURIComponent;

  return {
    health: () => request("GET", "/health"),

    listPrograms: async (params = {}) => page(await request("GET", `/programs${q(params)}`)),
    getProgram: async (programId) => (await request("GET", `/programs/${id(programId)}`)).program,
    createProgram: async ({ name, source, description = "" }) =>
      (await request("POST", "/programs", { body: { name, source, description } })).program,
    updateProgram: async (programId, revision, { name, source, description = "" }) =>
      (await request("PUT", `/programs/${id(programId)}`,
        { body: { name, source, description }, revision })).program,
    deleteProgram: (programId, revision) =>
      request("DELETE", `/programs/${id(programId)}`, { revision }),

    listCollections: async (params = {}) => page(await request("GET", `/collections${q(params)}`)),
    getCollection: async (collectionId) =>
      (await request("GET", `/collections/${id(collectionId)}`)).collection,
    createCollection: async ({ name, description = "" }) =>
      (await request("POST", "/collections", { body: { name, description } })).collection,
    updateCollection: async (collectionId, revision, { name, description = "" }) =>
      (await request("PUT", `/collections/${id(collectionId)}`,
        { body: { name, description }, revision })).collection,
    deleteCollection: (collectionId, revision) =>
      request("DELETE", `/collections/${id(collectionId)}`, { revision }),

    addCase: async (collectionId, revision, { name, source, expected, description = "" }) =>
      (await request("POST", `/collections/${id(collectionId)}/cases`,
        { body: { name, source, expected, description }, revision })).collection,
    updateCase: async (collectionId, caseId, revision, { name, source, expected, description = "" }) =>
      (await request("PUT", `/collections/${id(collectionId)}/cases/${id(caseId)}`,
        { body: { name, source, expected, description }, revision })).collection,
    deleteCase: async (collectionId, caseId, revision) =>
      (await request("DELETE", `/collections/${id(collectionId)}/cases/${id(caseId)}`,
        { revision })).collection,
  };
}
