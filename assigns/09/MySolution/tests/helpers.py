"""Shared test helpers: a schema-checking wrapper around Flask's test client."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from studio_db.api import create_app
from studio_db.config import Limits
from studio_db.service import StudioService

OPENAPI = json.loads((Path(__file__).resolve().parents[1] / "openapi.json").read_text(encoding="utf-8"))
FACTORIAL = ("let fact = fix f(n: sint): sint => if n <= 0 then 1 else n * f(n - 1) "
             "in fact(6) end")


def schema_for(name: str) -> Draft202012Validator:
    root = {"$ref": f"#/components/schemas/{name}", "components": OPENAPI["components"]}
    return Draft202012Validator(root)


SCHEMAS = {name: schema_for(name) for name in
           ("Health", "ProgramEnvelope", "CollectionEnvelope", "ProgramPage",
            "CollectionPage", "Error")}


class Api:
    """Calls the API like a client would and checks every response against
    openapi.json plus the documented headers."""

    def __init__(self, app):
        self.app = app
        self.client = app.test_client()

    def call(self, method: str, path: str, body=None, *, if_match=None, raw=None,
             content_type="application/json", headers=None):
        all_headers = dict(headers or {})
        if if_match is not None:
            all_headers["If-Match"] = if_match
        kwargs = {"headers": all_headers}
        if body is not None:
            kwargs["data"] = json.dumps(body)
            kwargs["content_type"] = content_type
        elif raw is not None:
            kwargs["data"] = raw
            kwargs["content_type"] = content_type
        response = self.client.open("/api/v1" + path, method=method, **kwargs)
        self._check(response)
        return response

    def _check(self, response):
        if response.status_code == 204:
            assert response.data == b"", "204 must have no body"
            return
        assert response.mimetype == "application/json", response.content_type
        payload = response.get_json()
        if response.status_code >= 400:
            SCHEMAS["Error"].validate(payload)
        elif "program" in payload:
            SCHEMAS["ProgramEnvelope"].validate(payload)
            assert response.headers["ETag"] == f'"{payload["program"]["revision"]}"'
        elif "collection" in payload:
            SCHEMAS["CollectionEnvelope"].validate(payload)
            assert response.headers["ETag"] == f'"{payload["collection"]["revision"]}"'
        elif "items" in payload:
            items = payload["items"]
            kind = "CollectionPage" if items and "cases" in items[0] else "ProgramPage"
            SCHEMAS[kind].validate(payload)
        else:
            SCHEMAS["Health"].validate(payload)

    # Convenience wrappers ------------------------------------------------
    def get(self, path, **kw): return self.call("GET", path, **kw)
    def post(self, path, body=None, **kw): return self.call("POST", path, body, **kw)
    def put(self, path, body=None, **kw): return self.call("PUT", path, body, **kw)
    def delete(self, path, **kw): return self.call("DELETE", path, **kw)

    def new_program(self, name="factorial", source=FACTORIAL, **extra):
        r = self.post("/programs", {"name": name, "source": source, **extra})
        assert r.status_code == 201, r.get_json()
        return r.get_json()["program"]

    def new_collection(self, name="basics", **extra):
        r = self.post("/collections", {"name": name, **extra})
        assert r.status_code == 201, r.get_json()
        return r.get_json()["collection"]

    def add_case(self, collection, name, source="1 + 2", expected=None, **extra):
        expected = expected or {"kind": "value", "value": "3"}
        r = self.post(f"/collections/{collection['id']}/cases",
                      {"name": name, "source": source, "expected": expected, **extra},
                      if_match=f'"{collection["revision"]}"')
        assert r.status_code == 201, r.get_json()
        return r.get_json()["collection"]


def make_api(limits: Limits | None = None, **service_kwargs) -> Api:
    service = StudioService(limits=limits, **service_kwargs)
    return Api(create_app(service))


def error_code(response) -> str:
    return response.get_json()["error"]["code"]
