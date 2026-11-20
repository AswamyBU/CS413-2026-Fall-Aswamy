"""RPC method handlers: parameter validation plus calls into the StreamTable.

Every parameter is validated *before* a stream is allocated or forced.
"""

from __future__ import annotations

from .errors import INVALID_PARAMS, RpcError
from .solver import MAX_SIZE, MIN_SIZE
from .streams import StreamTable

VERSION = "1.0"
MIN_LIMIT, MAX_LIMIT = 1, 32
MAX_STREAM_ID_LENGTH = 64


def _invalid(message: str, **data) -> RpcError:
    return RpcError(INVALID_PARAMS, f"Invalid params: {message}", data or None)


def _check_keys(params: dict, required: set[str], optional: set[str] = frozenset()) -> None:
    missing = sorted(required - set(params))
    if missing:
        raise _invalid("missing " + ", ".join(missing), missing=missing)
    unexpected = sorted(set(params) - required - set(optional))
    if unexpected:
        raise _invalid("unexpected " + ", ".join(u[:40] for u in unexpected[:5]),
                       unexpected=[u[:40] for u in unexpected[:5]])


def _int_in_range(params: dict, name: str, low: int, high: int) -> int:
    value = params[name]
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise _invalid(f"{name} must be an integer from {low} to {high}",
                       param=name, min=low, max=high)
    return value


def _stream_id(params: dict) -> str:
    value = params["stream_id"]
    if not isinstance(value, str) or not value or len(value) > MAX_STREAM_ID_LENGTH:
        raise _invalid("stream_id must be a nonempty string", param="stream_id")
    return value


class QueensService:
    def __init__(self, table: StreamTable):
        self.table = table

    def methods(self) -> dict:
        return {
            "service.health": self.health,
            "queens.open": self.open,
            "queens.next": self.next,
            "queens.close": self.close,
        }

    def health(self, params: dict) -> dict:
        _check_keys(params, set())
        return {"status": "ok", "version": VERSION}

    def open(self, params: dict) -> dict:
        _check_keys(params, {"size"})
        size = _int_in_range(params, "size", MIN_SIZE, MAX_SIZE)
        return {"stream_id": self.table.open(size), "size": size}

    def next(self, params: dict) -> dict:
        _check_keys(params, {"stream_id"}, {"limit"})
        stream_id = _stream_id(params)
        limit = _int_in_range(params, "limit", MIN_LIMIT, MAX_LIMIT) if "limit" in params else 1
        return self.table.next(stream_id, limit)

    def close(self, params: dict) -> dict:
        _check_keys(params, {"stream_id"})
        return self.table.close(_stream_id(params))
