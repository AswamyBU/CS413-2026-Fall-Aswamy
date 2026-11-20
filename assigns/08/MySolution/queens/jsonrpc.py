"""JSON-RPC 2.0 envelope handling, independent of HTTP and of the solver.

Adapted from my Assign07 dispatcher. `Dispatcher.handle_body(raw_bytes)`
returns a response dict, or None when nothing should be sent (notification).
Batches are not supported in this service: a JSON array body gets a single
-32600 Invalid Request response (see README "Limitations").
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

from .errors import (INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST,
                     METHOD_NOT_FOUND, PARSE_ERROR, RpcError)

log = logging.getLogger("queens.rpc")

_ENVELOPE_KEYS = frozenset({"jsonrpc", "method", "params", "id"})


def _reject_constant(name: str):
    raise ValueError(f"{name} is not valid JSON")


def error_response(request_id, error: RpcError) -> dict:
    return {"jsonrpc": "2.0", "error": error.to_dict(), "id": request_id}


def success_response(request_id, result) -> dict:
    return {"jsonrpc": "2.0", "result": result, "id": request_id}


def _valid_id(value) -> bool:
    return value is None or isinstance(value, str) or (
        isinstance(value, (int, float)) and not isinstance(value, bool))


def envelope_problem(request) -> str | None:
    """Return why `request` is not a valid JSON-RPC 2.0 Request, or None."""
    if not isinstance(request, dict):
        return "request must be a JSON object"
    unexpected = set(request) - _ENVELOPE_KEYS
    if unexpected:
        return "unexpected member(s): " + ", ".join(sorted(unexpected)[:5])
    if request.get("jsonrpc") != "2.0":
        return 'jsonrpc must be exactly "2.0"'
    if not isinstance(request.get("method"), str) or not request["method"]:
        return "method must be a nonempty string"
    if "params" in request and not isinstance(request["params"], (dict, list)):
        return "params must be an object or array when present"
    if "id" in request and not _valid_id(request["id"]):
        return "id must be a string, number, or null"
    return None


class Dispatcher:
    def __init__(self, methods: dict[str, Callable[[dict], object]]):
        # A fixed table: requests can only select one of these names.
        self.methods = dict(methods)

    def handle_body(self, body: bytes):
        try:
            payload = json.loads(body.decode("utf-8"), parse_constant=_reject_constant)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return error_response(None, RpcError(PARSE_ERROR, "Parse error: body is not valid JSON"))
        if isinstance(payload, list):
            return error_response(None, RpcError(
                INVALID_REQUEST, "Invalid Request: batch requests are not supported",
                {"reason": "batch requests are not supported"}))
        return self.handle_request(payload)

    def handle_request(self, request):
        problem = envelope_problem(request)
        if problem:
            # The envelope cannot be trusted, so neither can its id: use null.
            return error_response(None, RpcError(
                INVALID_REQUEST, f"Invalid Request: {problem}", {"reason": problem}))

        is_notification = "id" not in request
        request_id = request.get("id")
        try:
            response = success_response(request_id, self._call(request["method"],
                                                               request.get("params", {})))
        except RpcError as error:
            response = error_response(request_id, error)
        except Exception:
            # Never leak tracebacks, paths or LAMBDA3 values to the client.
            log.exception("unexpected failure in %r (id=%r)", request["method"][:100], request_id)
            response = error_response(request_id, RpcError(INTERNAL_ERROR))
        return None if is_notification else response

    def _call(self, name: str, params):
        method = self.methods.get(name)
        if method is None:
            raise RpcError(METHOD_NOT_FOUND, "Method not found",
                           {"method": name[:100], "available": sorted(self.methods)})
        if not isinstance(params, dict):
            raise RpcError(INVALID_PARAMS,
                           "Invalid params: params must be an object (by-name), not an array")
        return method(params)
