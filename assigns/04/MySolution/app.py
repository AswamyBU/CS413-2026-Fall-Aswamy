"""Flask entry point: composition root plus the thin HTTP layer.

Each route unpacks the request, calls one WorkbenchController method, and
returns the resulting model snapshot as JSON.  No state rules or language
logic live here.

Run:  python app.py      then open http://127.0.0.1:5000/
"""

from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory

from backend import Lambda1Backend
from contract import LanguageBackend
from controller import WorkbenchController
from model import MAX_SOURCE_BYTES, WorkbenchModel

HOST = "127.0.0.1"   # loopback only
PORT = 5000


def create_app(backend: LanguageBackend | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    # Leave headroom for multipart overhead; the model enforces the real limit.
    app.config["MAX_CONTENT_LENGTH"] = MAX_SOURCE_BYTES * 2
    ctl = WorkbenchController(WorkbenchModel(), backend or Lambda1Backend())
    app.extensions["workbench"] = ctl

    def body_text() -> str:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        return text if isinstance(text, str) else ""

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/state")
    def state():
        return jsonify(ctl.state())

    @app.post("/api/source/upload")
    def upload():
        f = request.files.get("file")
        if f is None:
            return jsonify(ctl.upload("", b""))
        return jsonify(ctl.upload(f.filename or "upload", f.read()))

    @app.post("/api/source/example/<key>")
    def example(key: str):
        return jsonify(ctl.choose_example(key))

    @app.post("/api/source/manual")
    def manual():
        return jsonify(ctl.manual_input())

    @app.put("/api/draft")
    def edit():
        return jsonify(ctl.edit(body_text()))

    @app.post("/api/draft/apply")
    def apply():
        return jsonify(ctl.apply())

    @app.post("/api/draft/discard")
    def discard():
        return jsonify(ctl.discard())

    @app.post("/api/action/<op>")
    def action(op: str):
        return jsonify(ctl.run(op))

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(ctl.reject(f"Upload exceeds the {MAX_SOURCE_BYTES}-byte limit.")), 413

    return app


if __name__ == "__main__":
    # threaded=True lets /api/state be served while Interpret is running;
    # the reloader is off because Interpret spawns child processes.
    create_app().run(host=HOST, port=PORT, threaded=True, use_reloader=False)
