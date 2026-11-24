"""API errors: an HTTP status, a stable machine-readable code, and details."""

INVALID_REQUEST = "invalid_request"
RECORD_NOT_FOUND = "record_not_found"
METHOD_NOT_ALLOWED = "method_not_allowed"
DUPLICATE_NAME = "duplicate_name"
REVISION_CONFLICT = "revision_conflict"
CAPACITY_LIMIT = "capacity_limit"
PAYLOAD_TOO_LARGE = "payload_too_large"
UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
PRECONDITION_REQUIRED = "precondition_required"
INTERNAL_ERROR = "internal_error"


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, **details):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details

    def body(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, **self.details}}


def invalid(message: str, **details) -> ApiError:
    return ApiError(400, INVALID_REQUEST, message, **details)


def not_found(message: str = "Record not found") -> ApiError:
    return ApiError(404, RECORD_NOT_FOUND, message)
