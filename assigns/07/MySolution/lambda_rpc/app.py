"""HTTP transport: one endpoint, POST /rpc.

HTTP status describes the transport, not the RPC outcome:
  200  a JSON-RPC response (success *or* error, including -32700/-32600)
  204  nothing to return (notification, or batch of only notifications)
  413  body larger than the configured limit
  415  Content-Type is not application/json
  404/405  wrong URL or HTTP method
"""

import json
import logging

from flask import Flask, Response, request
from werkzeug.exceptions import HTTPException

from .config import Limits
from .jsonrpc import Dispatcher
from .service import LambdaService

JSON_MEDIA_TYPE = "application/json"


def create_app(service: LambdaService | None = None, limits: Limits | None = None) -> Flask:
    limits = limits or (service.limits if service else Limits.from_env())
    service = service or LambdaService(limits)
    dispatcher = Dispatcher(service.methods(), max_batch_items=limits.max_batch_items)

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = limits.max_body_bytes
    app.extensions["lambda_rpc"] = {"service": service, "dispatcher": dispatcher}
    logging.getLogger("lambda_rpc").setLevel(logging.INFO)

    @app.post("/rpc")
    def rpc():
        if request.mimetype != JSON_MEDIA_TYPE:
            return _transport_error(415, "Content-Type must be application/json")
        response = dispatcher.handle_body(request.get_data(cache=False))
        if response is None:
            return Response(status=204)
        return Response(json.dumps(response), status=200, mimetype=JSON_MEDIA_TYPE)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        # Plain text on purpose: these are transport failures, not JSON-RPC responses.
        return _transport_error(error.code or 500, error.name)

    return app


def _transport_error(status: int, message: str) -> Response:
    return Response(message + "\n", status=status, mimetype="text/plain")
