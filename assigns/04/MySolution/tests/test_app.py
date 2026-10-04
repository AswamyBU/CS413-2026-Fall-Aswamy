"""HTTP layer (Flask test client) and architectural-boundary checks."""

import ast
import io
from pathlib import Path

import pytest

from app import create_app
from conftest import ROOT, example


@pytest.fixture
def client():
    return create_app().test_client()


def test_index_and_static_assets_served(client):
    assert b"LAMBDA Workbench" in client.get("/").data
    assert client.get("/static/view.js").status_code == 200


def test_example_lint_interpret_over_http(client):
    s = client.post("/api/source/example/fibonacci").get_json()
    assert s["source"] == {"name": "Fibonacci", "revision": 1, "text": example("fibonacci")}
    assert client.post("/api/action/lint").get_json()["results"][-1]["status"] == "ok"
    out = client.post("/api/action/interpret").get_json()["results"][-1]
    assert out["output"] == "D0Vint(arg1=610)" and out["revision"] == 1


def test_upload_good_and_bad_files(client):
    good = client.post("/api/source/upload", data={
        "file": (io.BytesIO(example("arithmetic").encode()), "arith.lambda")})
    assert good.get_json()["source"]["name"] == "arith.lambda"
    bad = client.post("/api/source/upload", data={
        "file": (io.BytesIO((ROOT / "examples/invalid_utf8.lambda").read_bytes()), "bad.lambda")})
    snap = bad.get_json()
    assert "UTF-8" in snap["notice"]["text"]
    assert snap["source"]["name"] == "arith.lambda"          # previous source kept


def test_draft_edit_apply_discard_over_http(client):
    client.post("/api/source/manual")
    s = client.put("/api/draft", json={"text": 'D0Evar("<b>bold</b>")'}).get_json()
    assert s["dirty"] and not any(a["enabled"] for a in s["actions"])
    s = client.post("/api/draft/apply").get_json()
    r = client.post("/api/action/lint").get_json()["results"][-1]
    # The JSON carries the text verbatim; the view inserts it with textContent.
    assert "<b>bold</b>" in r["summary"]
    client.put("/api/draft", json={"text": "   "})
    s = client.post("/api/draft/apply").get_json()
    assert s["notice"]["level"] == "error" and s["source"]["revision"] == 1
    s = client.post("/api/draft/discard").get_json()
    assert not s["dirty"] and s["draft"]["text"] == 'D0Evar("<b>bold</b>")'


# ---- architectural boundaries ---------------------------------------------

def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_model_does_not_depend_on_web_or_language_tools():
    assert imports_of(ROOT / "model.py") - {"__future__", "dataclasses"} == {"contract"}


def test_controller_does_not_depend_on_flask_or_lambda1():
    deps = imports_of(ROOT / "controller.py")
    assert not deps & {"flask", "lambda1", "backend", "reader"}


def test_view_renders_text_literally_and_has_no_language_logic():
    js = (ROOT / "static/view.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js
    assert "D0E" not in js and "fvset" not in js and "evaluate" not in js
