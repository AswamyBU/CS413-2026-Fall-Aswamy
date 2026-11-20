"""HTTP transport (Python standard library only).

  POST /rpc   JSON-RPC 2.0, Content-Type: application/json
              200 + JSON body  for every call, success or JSON-RPC error
              204, no body     for a valid notification
              413              body larger than MAX_BODY_BYTES
              415              Content-Type is not application/json
              411              no Content-Length
  GET  /      the browser client (web/index.html) and its static assets
  anything else: 404 / 405 (plain text)
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .jsonrpc import Dispatcher
from .service import QueensService
from .solver import make_backend
from .streams import DEFAULT_MAX_STREAMS, DEFAULT_TTL_SECONDS, StreamTable

MAX_BODY_BYTES = 64 * 1024
WEB_DIR = Path(__file__).resolve().parents[1] / "web"
# Only these files are served; nothing is resolved from the request path.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/rpc.js": ("rpc.js", "text/javascript; charset=utf-8"),
    "/board.js": ("board.js", "text/javascript; charset=utf-8"),
    "/player.js": ("player.js", "text/javascript; charset=utf-8"),
    "/main.js": ("main.js", "text/javascript; charset=utf-8"),
}

log = logging.getLogger("queens.http")


def build_service(backend: str = "compiled", *, ttl_seconds: float = DEFAULT_TTL_SECONDS,
                  max_streams: int = DEFAULT_MAX_STREAMS) -> QueensService:
    table = StreamTable(make_backend(backend), ttl_seconds=ttl_seconds, max_streams=max_streams)
    return QueensService(table)


class QueensHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, service: QueensService):
        self.service = service
        self.dispatcher = Dispatcher(service.methods())
        super().__init__(address, QueensRequestHandler)


class QueensRequestHandler(BaseHTTPRequestHandler):
    server: QueensHTTPServer
    server_version = "QueensRPC/1.0"
    sys_version = ""

    def log_message(self, fmt, *args):  # route through logging, not stderr
        log.debug("%s - " + fmt, self.address_string(), *args)

    def _plain(self, status: int, message: str) -> None:
        body = (message + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/rpc":
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        entry = STATIC_FILES.get(path)
        if entry is None:
            return self._plain(404, "Not Found")
        name, content_type = entry
        body = (WEB_DIR / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/rpc":
            return self._plain(404, "Not Found")
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            return self._plain(415, "Content-Type must be application/json")
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            return self._plain(411, "Content-Length required")
        try:
            length = int(length_header)
        except ValueError:
            return self._plain(400, "Bad Content-Length")
        if length < 0 or length > MAX_BODY_BYTES:
            return self._plain(413, "Request body too large")
        response = self.server.dispatcher.handle_body(self.rfile.read(length))
        if response is None:
            self.send_response(204)
            self.end_headers()
            return
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(host: str = "127.0.0.1", port: int = 8000,
                service: QueensService | None = None) -> QueensHTTPServer:
    return QueensHTTPServer((host, port), service or build_service())
