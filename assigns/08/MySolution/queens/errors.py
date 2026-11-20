"""JSON-RPC error codes and the exception that carries them."""

# Standard JSON-RPC 2.0 errors.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Application errors (implementation-defined server-error range).
STREAM_NOT_FOUND = -32001   # unknown, closed, or expired stream_id
TOO_MANY_STREAMS = -32002   # open-stream cap reached; close one or retry later

DEFAULT_MESSAGES = {
    PARSE_ERROR: "Parse error",
    INVALID_REQUEST: "Invalid Request",
    METHOD_NOT_FOUND: "Method not found",
    INVALID_PARAMS: "Invalid params",
    INTERNAL_ERROR: "Internal error",
    STREAM_NOT_FOUND: "Stream not found",
    TOO_MANY_STREAMS: "Too many open streams",
}


class RpcError(Exception):
    """Becomes the `error` member of a JSON-RPC response."""

    def __init__(self, code: int, message: str | None = None, data: object = None):
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "Server error")
        self.data = data
        super().__init__(self.message)

    def to_dict(self) -> dict:
        error = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error
