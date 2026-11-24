"""Compose the studio: one origin, three independent parts.

    /                 the studio page (web/)                 static files
    /api/v1/...       the database service (studio_db)       stores data only
    /lambda/rpc       the Assign07 LAMBDA3 JSON-RPC service  runs LAMBDA3

The two services stay separate WSGI applications. They are only mounted side
by side (werkzeug DispatcherMiddleware) so the browser can reach both without
cross-origin requests. studio_db never imports LAMBDA3; the Assign07 app is
imported unchanged from assigns/07/MySolution (override with LAMBDA_RPC_DIR).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, send_from_directory
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from studio_db.api import create_app as create_db_app
from studio_db.errors import ApiError, not_found
from studio_db.service import StudioService

HERE = Path(__file__).resolve().parent
WEB_DIR = HERE / "web"
STUDIO_FILES = {"index.html", "studio.css", "app.js", "storage.js", "lambda.js",
                "runner.js", "drafts.js"}
LAMBDA_RPC_DIR = Path(os.environ.get("LAMBDA_RPC_DIR")
                      or HERE.parents[1] / "07" / "MySolution")


def load_lambda_app():
    """Import the Assign07 Flask app factory and build its app."""
    if str(LAMBDA_RPC_DIR) not in sys.path:
        sys.path.insert(0, str(LAMBDA_RPC_DIR))
    from lambda_rpc.app import create_app as create_lambda_app  # Assign07, unchanged
    return create_lambda_app()


def create_studio_app(service: StudioService | None = None, *, with_lambda: bool = True) -> Flask:
    app = create_db_app(service)

    @app.get("/")
    def studio_index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/<name>")
    def studio_file(name: str):
        if name not in STUDIO_FILES:
            raise not_found("no such route")
        response = send_from_directory(WEB_DIR, name)
        response.headers["Cache-Control"] = "no-store"
        return response

    if with_lambda:
        app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/lambda": load_lambda_app()})
    return app


__all__ = ["create_studio_app", "load_lambda_app", "ApiError"]
