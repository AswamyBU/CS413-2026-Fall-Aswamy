"""JSON-RPC error codes and the exception used to carry them."""

# Standard JSON-RPC 2.0 errors.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Application errors (server-error range -32000..-32099).
LAMBDA_SYNTAX_ERROR = -32010
LAMBDA_TYPE_ERROR = -32011
EXECUTION_TIMEOUT = -32012
EXECUTION_ERROR = -32013
RESOURCE_LIMIT = -32014

DEFAULT_MESSAGES = {
    PARSE_ERROR: "Parse error",
    INVALID_REQUEST: "Invalid Request",
    METHOD_NOT_FOUND: "Method not found",
    INVALID_PARAMS: "Invalid params",
    INTERNAL_ERROR: "Internal error",
    LAMBDA_SYNTAX_ERROR: "LAMBDA syntax error",
    LAMBDA_TYPE_ERROR: "LAMBDA type error",
    EXECUTION_TIMEOUT: "Execution timeout",
    EXECUTION_ERROR: "LAMBDA runtime error",
    RESOURCE_LIMIT: "Resource limit exceeded",
}


class RpcError(Exception):
    """An error that becomes the `error` member of a JSON-RPC response."""

    def __init__(self, code: int, message: str | None = None, data: object = None):
        super().__init__(message or DEFAULT_MESSAGES.get(code, "Server error"))
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "Server error")
        self.data = data

    def to_dict(self) -> dict:
        error = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error
