"""HTTP layer (Flask): routes, status codes, headers, JSON encoding.

Route handlers stay thin: check the route IDs, hand the If-Match header and
a deferred body reader to the service, and turn the returned record into
JSON with an ETag. Every error, including Flask's own 404/405/413, leaves as
the documented JSON error envelope.
"""

from __future__ import annotations

import json
import logging

from flask import Blueprint, Flask, Response, request
from werkzeug.exceptions import HTTPException

from . import validation
from .config import API_VERSION, Limits
from .errors import (INTERNAL_ERROR, METHOD_NOT_ALLOWED, PAYLOAD_TOO_LARGE,
                     RECORD_NOT_FOUND, UNSUPPORTED_MEDIA_TYPE, ApiError, invalid)
from .service import StudioService
from .store import COLLECTIONS, PROGRAMS

log = logging.getLogger("studio_db")
PREFIX = "/api/v1"


def _json(payload, status: int = 200, etag_revision: int | None = None,
          location: str | None = None) -> Response:
    response = Response(json.dumps(payload), status=status,
                        content_type="application/json; charset=utf-8")
    if etag_revision is not None:
        response.headers["ETag"] = f'"{etag_revision}"'
    if location:
        response.headers["Location"] = location
    return response


def _error(error: ApiError) -> Response:
    return _json(error.body(), error.status)


def _deferred_body():
    """Read the request now (outside the service lock); validate it later.

    Returns a thunk that yields the decoded JSON or raises the 415/400 that
    applies, so the service can report 404/428 first (API.md section 4).
    """
    mimetype = request.mimetype
    raw = request.get_data(cache=False)  # raises 413 beyond MAX_CONTENT_LENGTH

    def body():
        if mimetype != "application/json":
            raise ApiError(415, UNSUPPORTED_MEDIA_TYPE,
                           "request body must be sent as Content-Type: application/json")
        try:
            return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise invalid("request body is not valid JSON") from None
    return body


def _reject_constant(name: str):
    raise ValueError(f"{name} is not valid JSON")  # NaN / Infinity


def _if_match():
    return request.headers.get("If-Match")


def _page_args():
    return {key: request.args.getlist(key) for key in request.args.keys()}


def create_api(service: StudioService) -> Blueprint:
    api = Blueprint("studio_db", __name__, url_prefix=PREFIX)
    limits = service.limits

    @api.get("/health")
    def health():
        return _json({"status": "ok", "version": API_VERSION})

    # ---------------------------------------------------------- programs

    @api.post("/programs")
    def create_program():
        program = service.create_program(_deferred_body())
        return _json({"program": program.to_json()}, 201, program.revision,
                     f"{PREFIX}/programs/{program.id}")

    @api.get("/programs")
    def list_programs():
        limit, cursor = validation.page_params(_page_args(), limits)
        items, next_cursor = service.list_page(PROGRAMS, limit, cursor)
        return _json({"items": [p.to_json() for p in items], "next_cursor": next_cursor})

    @api.get("/programs/<program_id>")
    def get_program(program_id):
        program = service.get_program(validation.check_id("program", program_id))
        return _json({"program": program.to_json()}, 200, program.revision)

    @api.put("/programs/<program_id>")
    def update_program(program_id):
        validation.check_id("program", program_id)
        program = service.update_program(program_id, _if_match(), _deferred_body())
        return _json({"program": program.to_json()}, 200, program.revision)

    @api.delete("/programs/<program_id>")
    def delete_program(program_id):
        service.delete_program(validation.check_id("program", program_id), _if_match())
        return Response(status=204)

    # ---------------------------------------------------------- collections

    @api.post("/collections")
    def create_collection():
        collection = service.create_collection(_deferred_body())
        return _json({"collection": collection.to_json()}, 201, collection.revision,
                     f"{PREFIX}/collections/{collection.id}")

    @api.get("/collections")
    def list_collections():
        limit, cursor = validation.page_params(_page_args(), limits)
        items, next_cursor = service.list_page(COLLECTIONS, limit, cursor)
        return _json({"items": [c.to_json() for c in items], "next_cursor": next_cursor})

    @api.get("/collections/<collection_id>")
    def get_collection(collection_id):
        collection = service.get_collection(validation.check_id("collection", collection_id))
        return _json({"collection": collection.to_json()}, 200, collection.revision)

    @api.put("/collections/<collection_id>")
    def update_collection(collection_id):
        validation.check_id("collection", collection_id)
        collection = service.update_collection(collection_id, _if_match(), _deferred_body())
        return _json({"collection": collection.to_json()}, 200, collection.revision)

    @api.delete("/collections/<collection_id>")
    def delete_collection(collection_id):
        service.delete_collection(validation.check_id("collection", collection_id), _if_match())
        return Response(status=204)

    # ---------------------------------------------------------- cases

    @api.post("/collections/<collection_id>/cases")
    def add_case(collection_id):
        validation.check_id("collection", collection_id)
        collection = service.add_case(collection_id, _if_match(), _deferred_body())
        return _json({"collection": collection.to_json()}, 201, collection.revision)

    @api.put("/collections/<collection_id>/cases/<case_id>")
    def update_case(collection_id, case_id):
        validation.check_id("collection", collection_id)
        validation.check_id("case", case_id, "case_id")
        collection = service.update_case(collection_id, case_id, _if_match(), _deferred_body())
        return _json({"collection": collection.to_json()}, 200, collection.revision)

    @api.delete("/collections/<collection_id>/cases/<case_id>")
    def delete_case(collection_id, case_id):
        validation.check_id("collection", collection_id)
        validation.check_id("case", case_id, "case_id")
        collection = service.delete_case(collection_id, case_id, _if_match())
        return _json({"collection": collection.to_json()}, 200, collection.revision)

    return api


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return _error(error)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        if error.code == 404:
            return _error(ApiError(404, RECORD_NOT_FOUND, "no such route"))
        if error.code == 405:
            response = _error(ApiError(405, METHOD_NOT_ALLOWED,
                                       f"{request.method} is not supported on this route"))
            allow = error.get_response().headers.get("Allow")
            if allow:
                response.headers["Allow"] = allow
            return response
        if error.code == 413:
            return _error(ApiError(413, PAYLOAD_TOO_LARGE, "request body is too large"))
        if error.code == 400:
            return _error(invalid("bad request"))
        return _error(ApiError(error.code or 500, INTERNAL_ERROR, error.name))

    @app.errorhandler(Exception)
    def unexpected(error: Exception):
        log.exception("unexpected failure on %s %s", request.method, request.path)
        return _error(ApiError(500, INTERNAL_ERROR, "internal server error"))


def create_app(service: StudioService | None = None, limits: Limits | None = None) -> Flask:
    """The database service as a standalone Flask app (API only)."""
    service = service or StudioService(limits=limits)
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = service.limits.max_body_bytes
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.extensions["studio_db"] = service
    app.register_blueprint(create_api(service))
    register_error_handlers(app)
    return app
