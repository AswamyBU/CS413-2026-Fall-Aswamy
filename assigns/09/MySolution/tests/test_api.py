"""HTTP-level tests for the database service (Flask test client).

Every response is validated against openapi.json by tests/helpers.Api.
Test data is created through the public API only.
"""

import re
import subprocess
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from studio_db.api import create_app
from studio_db.config import Limits
from studio_db.pagination import SnapshotTable
from studio_db.service import StudioService
from studio_db.store import MemoryStore

from tests.helpers import FACTORIAL, Api, error_code, make_api

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class HealthAndTransportTests(unittest.TestCase):
    def setUp(self):
        self.api = make_api()

    def test_health(self):
        r = self.api.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok", "version": "1.0"})
        self.assertEqual(r.mimetype, "application/json")

    def test_unknown_route_is_404_json(self):
        for path in ("/nope", "/programs/prg_0123456789abcdef/extra", "/collections/x/y/z/w"):
            r = self.api.get(path)
            self.assertEqual((r.status_code, error_code(r)), (404, "record_not_found"), path)
        r = self.api.client.get("/elsewhere")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error"]["code"], "record_not_found")

    def test_known_route_wrong_method_is_405_with_allow(self):
        cases = [("PATCH", "/programs/prg_0123456789abcdef"), ("DELETE", "/programs"),
                 ("PUT", "/collections"), ("GET", "/collections/col_0123456789abcdef/cases"),
                 ("POST", "/health")]
        for method, path in cases:
            r = self.api.call(method, path)
            self.assertEqual((r.status_code, error_code(r)), (405, "method_not_allowed"), path)
            self.assertIn("Allow", r.headers)

    def test_unsupported_media_type_is_415(self):
        r = self.api.post("/programs", raw='{"name":"a","source":"1"}', content_type="text/plain")
        self.assertEqual((r.status_code, error_code(r)), (415, "unsupported_media_type"))
        r = self.api.post("/programs", raw="name=a", content_type="application/x-www-form-urlencoded")
        self.assertEqual(r.status_code, 415)
        p = self.api.new_program()
        r = self.api.put(f"/programs/{p['id']}", raw='{"name":"a","source":"1"}',
                         content_type="text/plain", if_match='"1"')
        self.assertEqual(r.status_code, 415)
        self.assertEqual(self.api.get(f"/programs/{p['id']}").get_json()["program"]["revision"], 1)
        # charset parameter is fine
        r = self.api.post("/programs", raw='{"name":"b","source":"1"}',
                          content_type="application/json; charset=utf-8")
        self.assertEqual(r.status_code, 201)

    def test_malformed_json_and_non_object_bodies_are_400(self):
        for raw in ("{bad json", "", "[1,2]", '"text"', "42", '{"name": NaN, "source": "1"}', "\xff"):
            r = self.api.post("/programs", raw=raw)
            self.assertEqual((r.status_code, error_code(r)), (400, "invalid_request"), raw)

    def test_oversized_body_is_413(self):
        api = make_api(Limits(max_body_bytes=1024))
        r = api.post("/programs", {"name": "big", "source": "x" * 2000})
        self.assertEqual((r.status_code, error_code(r)), (413, "payload_too_large"))
        r = make_api().post("/programs", {"name": "big", "source": "1" + " " * (300 * 1024)})
        self.assertEqual(r.status_code, 413)

    def test_internal_errors_do_not_leak_details(self):
        class BrokenStore(MemoryStore):
            def put(self, kind, record):
                raise RuntimeError(r"secret C:\path\store.py")
        api = Api(create_app(StudioService(store=BrokenStore())))
        with self.assertLogs("studio_db", "ERROR"):
            r = api.post("/programs", {"name": "x", "source": "1"})
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.get_json(), {"error": {"code": "internal_error",
                                                  "message": "internal server error"}})
        self.assertNotIn(b"secret", r.data)

    def test_database_service_never_imports_lambda3(self):
        root = Path(__file__).resolve().parents[1]
        code = ("import sys; from studio_db.api import create_app; c = create_app().test_client(); "
                "c.post('/api/v1/programs', json={'name': 'p', 'source': '1 +'}); "
                "print(sorted(m for m in sys.modules if 'lambda' in m.lower()))")
        out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True,
                             text=True, timeout=60)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


class ProgramCrudTests(unittest.TestCase):
    def setUp(self):
        self.api = make_api()

    def test_create_get_update_delete(self):
        r = self.api.post("/programs", {"name": "  factorial  ", "source": FACTORIAL,
                                        "description": "six factorial"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers["ETag"], '"1"')
        p = r.get_json()["program"]
        self.assertEqual(r.headers["Location"], f"/api/v1/programs/{p['id']}")
        self.assertRegex(p["id"], r"^prg_[0-9a-f]{16}$")
        self.assertEqual((p["name"], p["source"], p["description"], p["revision"]),
                         ("factorial", FACTORIAL, "six factorial", 1))
        self.assertRegex(p["created_at"], ISO)
        self.assertEqual(p["created_at"], p["updated_at"])

        r = self.api.get(f"/programs/{p['id']}")
        self.assertEqual((r.status_code, r.headers["ETag"]), (200, '"1"'))
        self.assertEqual(r.get_json()["program"], p)

        time.sleep(0.002)
        r = self.api.put(f"/programs/{p['id']}", {"name": "fact5", "source": "5"}, if_match='"1"')
        self.assertEqual((r.status_code, r.headers["ETag"]), (200, '"2"'))
        q = r.get_json()["program"]
        self.assertEqual((q["id"], q["name"], q["source"], q["description"], q["revision"]),
                         (p["id"], "fact5", "5", "", 2))
        self.assertEqual(q["created_at"], p["created_at"])
        self.assertGreater(q["updated_at"], p["updated_at"])

        r = self.api.delete(f"/programs/{p['id']}", if_match='"2"')
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.api.get(f"/programs/{p['id']}").status_code, 404)

    def test_description_may_be_omitted_or_empty(self):
        self.assertEqual(self.api.new_program("a")["description"], "")
        self.assertEqual(self.api.new_program("b", description="")["description"], "")

    def test_list_returns_full_representations_in_creation_order(self):
        made = [self.api.new_program(f"p{i}", source=str(i)) for i in range(3)]
        r = self.api.get("/programs")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(body, {"items": made, "next_cursor": None})

    def test_timestamps_are_utc_iso8601(self):
        fixed = datetime(2026, 11, 23, 19, 5, 12, 345678, tzinfo=timezone.utc)
        api = make_api(clock=lambda: fixed)
        p = api.new_program()
        self.assertEqual(p["created_at"], "2026-11-23T19:05:12.345Z")
        other = datetime(2026, 11, 23, 14, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        api2 = make_api(clock=lambda: other)
        self.assertEqual(api2.new_program()["created_at"], "2026-11-23T19:00:00.000Z")


class CollectionAndCaseTests(unittest.TestCase):
    def setUp(self):
        self.api = make_api()

    def test_collection_create_get_update_delete(self):
        c = self.api.new_collection(" basics ", description="first")
        self.assertRegex(c["id"], r"^col_[0-9a-f]{16}$")
        self.assertEqual((c["name"], c["description"], c["revision"], c["cases"]),
                         ("basics", "first", 1, []))
        r = self.api.get(f"/collections/{c['id']}")
        self.assertEqual((r.status_code, r.headers["ETag"]), (200, '"1"'))
        r = self.api.put(f"/collections/{c['id']}", {"name": "renamed"}, if_match='"1"')
        self.assertEqual(r.get_json()["collection"]["name"], "renamed")
        self.assertEqual(r.get_json()["collection"]["description"], "")
        self.assertEqual(self.api.delete(f"/collections/{c['id']}", if_match='"2"').status_code, 204)
        self.assertEqual(self.api.get(f"/collections/{c['id']}").status_code, 404)

    def test_collection_put_changes_metadata_only(self):
        c = self.api.new_collection()
        c = self.api.add_case(c, "one")
        c = self.api.add_case(c, "two")
        before = [case for case in c["cases"]]
        r = self.api.put(f"/collections/{c['id']}", {"name": "basics", "description": "d"},
                         if_match='"3"')
        after = r.get_json()["collection"]
        self.assertEqual(after["cases"], before)
        self.assertEqual((after["revision"], after["description"]), (4, "d"))
        r = self.api.put(f"/collections/{c['id']}", {"name": "x", "cases": []}, if_match='"4"')
        self.assertEqual((r.status_code, r.get_json()["error"]["field"]), (400, "cases"))

    def test_add_update_delete_cases_in_order(self):
        c = self.api.new_collection()
        r = self.api.post(f"/collections/{c['id']}/cases",
                          {"name": "six", "source": FACTORIAL,
                           "expected": {"kind": "value", "value": "720"}, "description": "6!"},
                          if_match='"1"')
        self.assertEqual((r.status_code, r.headers["ETag"]), (201, '"2"'))
        c = r.get_json()["collection"]
        c = self.api.add_case(c, "syntax", "1 +", {"kind": "error", "category": "syntax"})
        c = self.api.add_case(c, "type", "1 + true", {"kind": "error", "category": "type"})
        self.assertEqual([x["name"] for x in c["cases"]], ["six", "syntax", "type"])
        self.assertEqual(c["revision"], 4)
        ids = [x["id"] for x in c["cases"]]
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(all(re.fullmatch(r"case_[0-9a-f]{16}", i) for i in ids))
        self.assertEqual(c["cases"][0], {"id": ids[0], "name": "six", "source": FACTORIAL,
                                         "expected": {"kind": "value", "value": "720"},
                                         "description": "6!"})

        # Update the middle case in place.
        r = self.api.put(f"/collections/{c['id']}/cases/{ids[1]}",
                         {"name": "syntax2", "source": "let in",
                          "expected": {"kind": "error", "category": "syntax"}},
                         if_match='"4"')
        self.assertEqual((r.status_code, r.headers["ETag"]), (200, '"5"'))
        c = r.get_json()["collection"]
        self.assertEqual([x["id"] for x in c["cases"]], ids)
        self.assertEqual((c["cases"][1]["name"], c["cases"][1]["source"],
                          c["cases"][1]["description"]), ("syntax2", "let in", ""))

        # Delete the first; the others keep their order.
        r = self.api.delete(f"/collections/{c['id']}/cases/{ids[0]}", if_match='"5"')
        self.assertEqual((r.status_code, r.headers["ETag"]), (200, '"6"'))
        self.assertEqual([x["id"] for x in r.get_json()["collection"]["cases"]], ids[1:])

        # Ordered retrieval through GET and through the list.
        got = self.api.get(f"/collections/{c['id']}").get_json()["collection"]
        self.assertEqual([x["id"] for x in got["cases"]], ids[1:])
        listed = self.api.get("/collections").get_json()["items"][0]
        self.assertEqual(listed, got)

    def test_unknown_case_id_is_404(self):
        c = self.api.new_collection()
        missing = "case_0123456789abcdef"
        for method in ("PUT", "DELETE"):
            body = {"name": "x", "source": "1", "expected": {"kind": "value", "value": "1"}}
            r = self.api.call(method, f"/collections/{c['id']}/cases/{missing}",
                              body if method == "PUT" else None)
            self.assertEqual((r.status_code, error_code(r)), (404, "record_not_found"))
        self.assertEqual(self.api.get(f"/collections/{c['id']}").get_json()["collection"]["revision"], 1)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.api = make_api(Limits(max_name_chars=10, max_source_bytes=20,
                                   max_description_chars=5, max_expected_value_chars=4))
        self.collection = self.api.new_collection("c")

    def assertInvalid(self, response, field):
        self.assertEqual(response.status_code, 400, response.get_json())
        error = response.get_json()["error"]
        self.assertEqual(error["code"], "invalid_request")
        self.assertEqual(error.get("field"), field)

    def post_case(self, body):
        return self.api.post(f"/collections/{self.collection['id']}/cases", body, if_match='"1"')

    def test_missing_fields(self):
        self.assertInvalid(self.api.post("/programs", {"source": "1"}), "name")
        self.assertInvalid(self.api.post("/programs", {"name": "a"}), "source")
        self.assertInvalid(self.api.post("/collections", {}), "name")
        self.assertInvalid(self.post_case({"name": "a", "source": "1"}), "expected")
        self.assertInvalid(self.post_case({"name": "a", "source": "1", "expected": {"kind": "value"}}),
                           "expected.value")
        self.assertInvalid(self.post_case({"name": "a", "source": "1", "expected": {"kind": "error"}}),
                           "expected.category")

    def test_wrong_types(self):
        for body, field in [({"name": 5, "source": "1"}, "name"),
                            ({"name": None, "source": "1"}, "name"),
                            ({"name": "a", "source": ["1"]}, "source"),
                            ({"name": "a", "source": "1", "description": 3}, "description")]:
            self.assertInvalid(self.api.post("/programs", body), field)
        self.assertInvalid(self.post_case({"name": "a", "source": "1", "expected": "720"}), "expected")
        self.assertInvalid(self.post_case({"name": "a", "source": "1",
                                           "expected": {"kind": "value", "value": 720}}), "expected.value")

    def test_blank_fields(self):
        self.assertInvalid(self.api.post("/programs", {"name": "   ", "source": "1"}), "name")
        self.assertInvalid(self.api.post("/programs", {"name": "a", "source": " \n\t"}), "source")
        self.assertInvalid(self.api.post("/programs", {"name": "a", "source": ""}), "source")
        self.assertInvalid(self.post_case({"name": "a", "source": "1",
                                           "expected": {"kind": "value", "value": ""}}), "expected.value")

    def test_oversized_fields_report_limit_and_actual(self):
        r = self.api.post("/programs", {"name": "a" * 11, "source": "1"})
        self.assertInvalid(r, "name")
        self.assertEqual((r.get_json()["error"]["limit"], r.get_json()["error"]["actual"]), (10, 11))
        self.assertEqual(self.api.post("/programs", {"name": "  " + "a" * 10 + "  ", "source": "1"}).status_code, 201)
        r = self.api.post("/programs", {"name": "s", "source": "é" * 11})  # 22 UTF-8 bytes
        self.assertInvalid(r, "source")
        self.assertEqual(r.get_json()["error"]["actual"], 22)
        self.assertInvalid(self.api.post("/programs", {"name": "d", "source": "1", "description": "123456"}),
                           "description")
        self.assertInvalid(self.post_case({"name": "a", "source": "1",
                                           "expected": {"kind": "value", "value": "12345"}}), "expected.value")

    def test_unknown_fields_rejected(self):
        for extra in ("id", "revision", "created_at", "updated_at", "extra"):
            self.assertInvalid(self.api.post("/programs", {"name": "a", "source": "1", extra: 1}), extra)
        self.assertInvalid(self.api.post("/collections", {"name": "a", "cases": []}), "cases")
        self.assertInvalid(self.post_case({"name": "a", "source": "1", "id": "case_0123456789abcdef",
                                           "expected": {"kind": "value", "value": "1"}}), "id")
        self.assertInvalid(self.post_case({"name": "a", "source": "1",
                                           "expected": {"kind": "value", "value": "1", "category": "type"}}),
                           "expected.category")
        self.assertInvalid(self.post_case({"name": "a", "source": "1",
                                           "expected": {"kind": "error", "category": "type", "value": "1"}}),
                           "expected.value")

    def test_expected_must_match_one_shape(self):
        for expected in ({"kind": "runtime", "category": "x"}, {"category": "syntax"},
                         {"kind": "error", "category": "runtime"}, {"kind": "error", "category": "timeout"}):
            r = self.post_case({"name": "a", "source": "1", "expected": expected})
            self.assertEqual(r.status_code, 400, expected)
        for expected in ({"kind": "error", "category": "syntax"}, {"kind": "error", "category": "type"},
                         {"kind": "value", "value": "720"}):
            c = self.api.get(f"/collections/{self.collection['id']}").get_json()["collection"]
            r = self.api.post(f"/collections/{c['id']}/cases",
                              {"name": expected.get("category", "v"), "source": "1", "expected": expected},
                              if_match=f'"{c["revision"]}"')
            self.assertEqual(r.status_code, 201)
            self.assertEqual(r.get_json()["collection"]["cases"][-1]["expected"], expected)

    def test_failed_validation_changes_nothing(self):
        p = self.api.new_program("keep", source="1")
        r = self.api.put(f"/programs/{p['id']}", {"name": "", "source": "2"}, if_match='"1"')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.api.get(f"/programs/{p['id']}").get_json()["program"], p)


class UniquenessAndIdTests(unittest.TestCase):
    def setUp(self):
        self.api = make_api()

    def test_duplicate_names_after_trimming(self):
        self.api.new_program("fact")
        r = self.api.post("/programs", {"name": "  fact ", "source": "1"})
        self.assertEqual((r.status_code, error_code(r), r.get_json()["error"]["field"]),
                         (409, "duplicate_name", "name"))
        self.assertEqual(self.api.post("/programs", {"name": "Fact", "source": "1"}).status_code, 201)
        self.api.new_collection("basics")
        self.assertEqual(error_code(self.api.post("/collections", {"name": "basics "})), "duplicate_name")

    def test_rename_into_duplicate_is_409_and_changes_nothing(self):
        self.api.new_program("a")
        b = self.api.new_program("b")
        r = self.api.put(f"/programs/{b['id']}", {"name": "a", "source": "1"}, if_match='"1"')
        self.assertEqual(error_code(r), "duplicate_name")
        self.assertEqual(self.api.get(f"/programs/{b['id']}").get_json()["program"], b)
        r = self.api.put(f"/programs/{b['id']}", {"name": " b ", "source": "2"}, if_match='"1"')
        self.assertEqual(r.status_code, 200)  # own name is fine

    def test_case_names_are_scoped_to_their_collection(self):
        c1 = self.api.add_case(self.api.new_collection("one"), "same")
        c2 = self.api.add_case(self.api.new_collection("two"), "same")  # other collection: ok
        self.api.new_program("same")  # other kind: ok
        r = self.api.post(f"/collections/{c1['id']}/cases",
                          {"name": " same ", "source": "1", "expected": {"kind": "value", "value": "1"}},
                          if_match='"2"')
        self.assertEqual(error_code(r), "duplicate_name")
        c1 = self.api.add_case(c1, "other")
        other_id = c1["cases"][1]["id"]
        r = self.api.put(f"/collections/{c1['id']}/cases/{other_id}",
                         {"name": "same", "source": "1", "expected": {"kind": "value", "value": "1"}},
                         if_match='"3"')
        self.assertEqual(error_code(r), "duplicate_name")
        self.assertEqual(self.api.get(f"/collections/{c1['id']}").get_json()["collection"]["revision"], 3)
        self.assertEqual(len(c2["cases"]), 1)

    def test_unknown_ids_are_404_even_without_if_match(self):
        for path in ("/programs/prg_0123456789abcdef", "/collections/col_0123456789abcdef"):
            self.assertEqual(self.api.get(path).status_code, 404)
            for if_match in (None, '"1"', '"99"'):
                r = self.api.put(path, {"name": "x", "source": "1"}, if_match=if_match)
                self.assertEqual((r.status_code, error_code(r)), (404, "record_not_found"))
                r = self.api.delete(path, if_match=if_match)
                self.assertEqual(r.status_code, 404)
        r = self.api.post("/collections/col_0123456789abcdef/cases",
                          {"name": "x", "source": "1", "expected": {"kind": "value", "value": "1"}})
        self.assertEqual(r.status_code, 404)

    def test_malformed_ids_are_400(self):
        for path in ("/programs/abc", "/programs/col_0123456789abcdef", "/programs/prg_0123456789ABCDEF",
                     "/collections/prg_0123456789abcdef"):
            r = self.api.get(path)
            self.assertEqual((r.status_code, error_code(r), r.get_json()["error"]["parameter"]),
                             (400, "invalid_request", "id"), path)
        c = self.api.new_collection()
        r = self.api.delete(f"/collections/{c['id']}/cases/nope", if_match='"1"')
        self.assertEqual((r.status_code, r.get_json()["error"]["parameter"]), (400, "case_id"))


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.api = make_api()

    def test_missing_if_match_is_428_on_every_mutation(self):
        p = self.api.new_program()
        c = self.api.add_case(self.api.new_collection(), "one")
        case_id = c["cases"][0]["id"]
        case_body = {"name": "two", "source": "1", "expected": {"kind": "value", "value": "1"}}
        calls = [("PUT", f"/programs/{p['id']}", {"name": "x", "source": "1"}),
                 ("DELETE", f"/programs/{p['id']}", None),
                 ("PUT", f"/collections/{c['id']}", {"name": "x"}),
                 ("DELETE", f"/collections/{c['id']}", None),
                 ("POST", f"/collections/{c['id']}/cases", case_body),
                 ("PUT", f"/collections/{c['id']}/cases/{case_id}", case_body),
                 ("DELETE", f"/collections/{c['id']}/cases/{case_id}", None)]
        for method, path, body in calls:
            r = self.api.call(method, path, body)
            self.assertEqual((r.status_code, error_code(r)), (428, "precondition_required"), path)
        self.assertEqual(self.api.get(f"/programs/{p['id']}").get_json()["program"]["revision"], 1)
        self.assertEqual(self.api.get(f"/collections/{c['id']}").get_json()["collection"]["revision"], 2)

    def test_malformed_if_match_is_400(self):
        p = self.api.new_program()
        for value in ('W/"1"', "*", "1", '"1", "2"', '"one"', '"0"', '""'):
            r = self.api.put(f"/programs/{p['id']}", {"name": "x", "source": "1"}, if_match=value)
            self.assertEqual((r.status_code, r.get_json()["error"].get("parameter")),
                             (400, "If-Match"), value)

    def test_each_update_increments_revision_by_one(self):
        p = self.api.new_program()
        for expected in range(2, 6):
            r = self.api.put(f"/programs/{p['id']}", {"name": "factorial", "source": FACTORIAL},
                             if_match=f'"{expected - 1}"')
            self.assertEqual(r.get_json()["program"]["revision"], expected)
            self.assertEqual(r.headers["ETag"], f'"{expected}"')

    def test_stale_update_is_409_and_leaves_record_unchanged(self):
        p = self.api.new_program()
        self.api.put(f"/programs/{p['id']}", {"name": "v2", "source": "2"}, if_match='"1"')
        current = self.api.get(f"/programs/{p['id']}").get_json()["program"]
        r = self.api.put(f"/programs/{p['id']}", {"name": "stale", "source": "3"}, if_match='"1"')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["error"]["code"], "revision_conflict")
        self.assertEqual(r.get_json()["error"]["current_revision"], 2)
        self.assertEqual(self.api.get(f"/programs/{p['id']}").get_json()["program"], current)
        # A future revision is also a conflict.
        r = self.api.put(f"/programs/{p['id']}", {"name": "x", "source": "3"}, if_match='"7"')
        self.assertEqual(r.get_json()["error"]["current_revision"], 2)

    def test_stale_delete_is_409_and_record_remains(self):
        p = self.api.new_program()
        self.api.put(f"/programs/{p['id']}", {"name": "v2", "source": "2"}, if_match='"1"')
        r = self.api.delete(f"/programs/{p['id']}", if_match='"1"')
        self.assertEqual((r.status_code, r.get_json()["error"]["current_revision"]), (409, 2))
        self.assertEqual(self.api.get(f"/programs/{p['id']}").status_code, 200)
        c = self.api.add_case(self.api.new_collection(), "one")
        r = self.api.delete(f"/collections/{c['id']}", if_match='"1"')
        self.assertEqual(r.status_code, 409)
        r = self.api.delete(f"/collections/{c['id']}/cases/{c['cases'][0]['id']}", if_match='"1"')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.api.get(f"/collections/{c['id']}").get_json()["collection"], c)

    def test_case_mutations_use_and_bump_collection_revision(self):
        c = self.api.new_collection()
        c = self.api.add_case(c, "a")                     # 2
        case_id = c["cases"][0]["id"]
        r = self.api.put(f"/collections/{c['id']}/cases/{case_id}",
                         {"name": "a", "source": "2", "expected": {"kind": "value", "value": "2"}},
                         if_match='"1"')                  # stale collection revision
        self.assertEqual((r.status_code, r.get_json()["error"]["current_revision"]), (409, 2))
        self.assertEqual(self.api.get(f"/collections/{c['id']}").get_json()["collection"], c)

    def test_stale_check_comes_after_404_and_428_and_validation(self):
        p = self.api.new_program()
        self.api.put(f"/programs/{p['id']}", {"name": "v2", "source": "2"}, if_match='"1"')
        r = self.api.put(f"/programs/{p['id']}", {"name": "", "source": "2"}, if_match='"1"')
        self.assertEqual(r.status_code, 400)  # body problems are reported before staleness


class PaginationTests(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        snapshots = SnapshotTable(max_snapshots=3, idle_seconds=60, clock=lambda: self.now[0])
        self.api = make_api(snapshots=snapshots)

    def pages(self, path, limit):
        items, cursor, count = [], None, 0
        while True:
            query = f"?limit={limit}" + (f"&cursor={cursor}" if cursor else "")
            body = self.api.get(path + query).get_json()
            self.assertLessEqual(len(body["items"]), limit)
            items += body["items"]
            count += 1
            cursor = body["next_cursor"]
            if cursor is None:
                return items, count

    def test_default_and_bounded_page_size(self):
        api = make_api()
        for i in range(55):
            api.new_program(f"p{i:02d}", source="1")
        first = api.get("/programs").get_json()
        self.assertEqual(len(first["items"]), 50)
        self.assertIsNotNone(first["next_cursor"])
        second = api.get(f"/programs?cursor={first['next_cursor']}").get_json()
        self.assertEqual(len(second["items"]), 5)
        self.assertIsNone(second["next_cursor"])
        self.assertEqual(len(api.get("/programs?limit=100").get_json()["items"]), 55)
        self.assertEqual(len(api.get("/programs?limit=1").get_json()["items"]), 1)

    def test_invalid_page_parameters(self):
        for query in ("limit=0", "limit=101", "limit=abc", "limit=-1", "limit=1.5", "limit=",
                      "limit=1&limit=2", "page=2", "cursor=", "cursor=not-a-cursor", "sort=name"):
            r = self.api.get(f"/programs?{query}")
            self.assertEqual((r.status_code, error_code(r)), (400, "invalid_request"), query)
            self.assertIn("parameter", r.get_json()["error"])

    def test_pages_cover_everything_in_order_without_overlap(self):
        made = [self.api.new_program(f"p{i}", source="1")["id"] for i in range(7)]
        items, count = self.pages("/programs", 3)
        self.assertEqual([p["id"] for p in items], made)
        self.assertEqual(count, 3)
        items, count = self.pages("/programs", 7)
        self.assertEqual(count, 1)

    def test_empty_list(self):
        self.assertEqual(self.api.get("/collections").get_json(), {"items": [], "next_cursor": None})

    def test_cursor_chain_is_a_stable_snapshot(self):
        made = [self.api.new_program(f"p{i}", source=str(i)) for i in range(4)]
        first = self.api.get("/programs?limit=2").get_json()
        # Change the live data after the snapshot was taken.
        self.api.put(f"/programs/{made[2]['id']}", {"name": "changed", "source": "x"}, if_match='"1"')
        self.api.delete(f"/programs/{made[3]['id']}", if_match='"1"')
        self.api.new_program("late", source="9")
        second = self.api.get(f"/programs?limit=2&cursor={first['next_cursor']}").get_json()
        self.assertEqual(second["items"], made[2:4])  # captured representations
        self.assertIsNone(second["next_cursor"])       # "late" is excluded
        # Re-reading a cursor returns the same page.
        again = self.api.get(f"/programs?limit=2&cursor={first['next_cursor']}").get_json()
        self.assertEqual(again["items"], made[2:4])
        # A fresh listing sees the live data.
        live = [p["name"] for p in self.api.get("/programs").get_json()["items"]]
        self.assertEqual(live, ["p0", "p1", "changed", "late"])

    def test_collection_cursor_snapshots_cases_too(self):
        cols = [self.api.new_collection(f"c{i}") for i in range(2)]
        first = self.api.get("/collections?limit=1").get_json()
        self.api.add_case(cols[1], "added later")
        second = self.api.get(f"/collections?limit=1&cursor={first['next_cursor']}").get_json()
        self.assertEqual(second["items"], [cols[1]])

    def test_cursor_is_bound_to_its_kind(self):
        for i in range(2):
            self.api.new_program(f"p{i}", source="1")
        cursor = self.api.get("/programs?limit=1").get_json()["next_cursor"]
        r = self.api.get(f"/collections?cursor={cursor}")
        self.assertEqual((r.status_code, r.get_json()["error"]["parameter"]), (400, "cursor"))

    def test_cursor_expires_after_idle_lifetime(self):
        for i in range(3):
            self.api.new_program(f"p{i}", source="1")
        cursor = self.api.get("/programs?limit=1").get_json()["next_cursor"]
        self.now[0] += 59
        cursor = self.api.get(f"/programs?limit=1&cursor={cursor}").get_json()["next_cursor"]
        self.now[0] += 61
        r = self.api.get(f"/programs?limit=1&cursor={cursor}")
        self.assertEqual((r.status_code, r.get_json()["error"]["parameter"]), (400, "cursor"))

    def test_least_recently_used_snapshot_is_evicted(self):
        for i in range(2):
            self.api.new_program(f"p{i}", source="1")
        oldest = self.api.get("/programs?limit=1").get_json()["next_cursor"]
        for _ in range(3):  # max_snapshots = 3
            self.api.get("/programs?limit=1")
        self.assertEqual(self.api.get(f"/programs?limit=1&cursor={oldest}").status_code, 400)


class CapacityTests(unittest.TestCase):
    def test_capacity_limits_are_409_and_change_nothing(self):
        api = make_api(Limits(max_programs=2, max_collections=1, max_cases_per_collection=2))
        api.new_program("a")
        api.new_program("b")
        r = api.post("/programs", {"name": "c", "source": "1"})
        self.assertEqual((r.status_code, error_code(r), r.get_json()["error"]["limit"]),
                         (409, "capacity_limit", 2))
        self.assertEqual(len(api.get("/programs").get_json()["items"]), 2)
        c = api.new_collection("only")
        self.assertEqual(error_code(api.post("/collections", {"name": "two"})), "capacity_limit")
        c = api.add_case(c, "1")
        c = api.add_case(c, "2")
        r = api.post(f"/collections/{c['id']}/cases",
                     {"name": "3", "source": "1", "expected": {"kind": "value", "value": "1"}},
                     if_match='"3"')
        self.assertEqual(error_code(r), "capacity_limit")
        self.assertEqual(api.get(f"/collections/{c['id']}").get_json()["collection"], c)
        # Deleting frees capacity.
        p = api.get("/programs").get_json()["items"][0]
        api.delete(f"/programs/{p['id']}", if_match='"1"')
        self.assertEqual(api.post("/programs", {"name": "c", "source": "1"}).status_code, 201)


class SlowStore(MemoryStore):
    """Widens the race window: every write pauses before it lands."""

    def put(self, kind, record):
        time.sleep(0.02)
        super().put(kind, record)


class ConcurrencyTests(unittest.TestCase):
    def race(self, api, requests):
        barrier = threading.Barrier(len(requests))
        results = [None] * len(requests)

        def worker(i, call):
            client = api.app.test_client()
            barrier.wait()
            results[i] = call(client)

        threads = [threading.Thread(target=worker, args=(i, call)) for i, call in enumerate(requests)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return [r.status_code for r in results]

    def test_exactly_one_of_two_same_revision_updates_wins(self):
        api = Api(create_app(StudioService(store=SlowStore())))
        for round_ in range(10):
            p = api.new_program(f"p{round_}")
            put = lambda name: (lambda c: c.put(f"/api/v1/programs/{p['id']}",
                                                json={"name": name, "source": "1"},
                                                headers={"If-Match": '"1"'}))
            statuses = self.race(api, [put(f"A{round_}"), put(f"B{round_}")])
            self.assertEqual(sorted(statuses), [200, 409])
            final = api.get(f"/programs/{p['id']}").get_json()["program"]
            self.assertEqual(final["revision"], 2)
            self.assertIn(final["name"], (f"A{round_}", f"B{round_}"))

    def test_concurrent_case_adds_with_same_revision(self):
        api = Api(create_app(StudioService(store=SlowStore())))
        c = api.new_collection()
        add = lambda name: (lambda cl: cl.post(f"/api/v1/collections/{c['id']}/cases",
                                               json={"name": name, "source": "1",
                                                     "expected": {"kind": "value", "value": "1"}},
                                               headers={"If-Match": '"1"'}))
        statuses = self.race(api, [add("x"), add("y"), add("z")])
        self.assertEqual(sorted(statuses), [201, 409, 409])
        final = api.get(f"/collections/{c['id']}").get_json()["collection"]
        self.assertEqual((final["revision"], len(final["cases"])), (2, 1))

    def test_concurrent_creates_with_same_name(self):
        api = Api(create_app(StudioService(store=SlowStore())))
        create = lambda cl: cl.post("/api/v1/programs", json={"name": "same", "source": "1"})
        statuses = self.race(api, [create] * 4)
        self.assertEqual(sorted(statuses), [201, 409, 409, 409])


class DeletionTests(unittest.TestCase):
    def setUp(self):
        self.api = make_api()

    def test_deleting_collection_removes_its_cases(self):
        c = self.api.add_case(self.api.add_case(self.api.new_collection(), "a"), "b")
        case_id = c["cases"][0]["id"]
        self.assertEqual(self.api.delete(f"/collections/{c['id']}", if_match='"3"').status_code, 204)
        self.assertEqual(self.api.get(f"/collections/{c['id']}").status_code, 404)
        r = self.api.put(f"/collections/{c['id']}/cases/{case_id}",
                         {"name": "a", "source": "1", "expected": {"kind": "value", "value": "1"}},
                         if_match='"3"')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.api.get("/collections").get_json()["items"], [])
        # A new collection with the same name starts empty.
        self.assertEqual(self.api.new_collection(c["name"])["cases"], [])

    def test_deleting_or_editing_program_leaves_case_snapshots(self):
        p = self.api.new_program("fact", source=FACTORIAL)
        c = self.api.add_case(self.api.new_collection(), "from program", source=p["source"],
                              expected={"kind": "value", "value": "720"})
        self.api.put(f"/programs/{p['id']}", {"name": "fact", "source": "0"}, if_match='"1"')
        self.api.delete(f"/programs/{p['id']}", if_match='"2"')
        after = self.api.get(f"/collections/{c['id']}").get_json()["collection"]
        self.assertEqual(after, c)
        self.assertEqual(after["cases"][0]["source"], FACTORIAL)


if __name__ == "__main__":
    unittest.main()
