"""HTTP-level tests for the LAMBDA3 JSON-RPC service (Flask test client).

Run from assigns/07/:
    python -m unittest discover -s MySolution/tests -t MySolution -v

Successful type-check / interpret / compile tests call the real LAMBDA3
implementation (and real worker processes). Test doubles are used only for
failure injection and the dispatch boundary.
"""

import json
import unittest
from pathlib import Path

import jsonschema

from lambda_rpc.app import create_app
from lambda_rpc.config import Limits
from lambda_rpc.errors import EXECUTION_TIMEOUT, RpcError
from lambda_rpc.service import LambdaService

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "schema" / "jsonrpc-lambda.schema.json").read_text()
)
RESPONSE_VALIDATOR = jsonschema.Draft202012Validator(
    {"$ref": "#/$defs/responseBody", "$defs": SCHEMA["$defs"]})
REQUEST_VALIDATOR = jsonschema.Draft202012Validator(
    {"$ref": "#/$defs/requestBody", "$defs": SCHEMA["$defs"]})

FACTORIAL = """\
let fact : sint -> sint =
  fix fact(n: sint): sint =>
    if n <= 1 then 1 else n * fact(n - 1)
in fact(6) end
"""
SLOW_FIB = """\
let fib : sint -> sint =
  fix fib(n: sint): sint => if n < 2 then n else fib(n - 1) + fib(n - 2)
in fib(40) end
"""
COLLECTION = (Path(__file__).resolve().parents[2] / "LAMBDA3" / "mytest" / "collections.lam").read_text()


class RpcTestCase(unittest.TestCase):
    """Shared helpers: post to /rpc and check HTTP + JSON-RPC envelopes."""

    service: LambdaService
    check_schema = True

    @classmethod
    def setUpClass(cls):
        cls.service = LambdaService(Limits(interpret_timeout=5.0))
        cls.client = create_app(cls.service).test_client()

    def post(self, payload=None, *, raw=None, content_type="application/json"):
        data = raw if raw is not None else json.dumps(payload)
        response = self.client.post("/rpc", data=data, content_type=content_type)
        body = response.get_json(silent=True) if response.data else None
        if response.status_code == 200:
            self.assertEqual(response.mimetype, "application/json")
            if self.check_schema:
                RESPONSE_VALIDATOR.validate(body)  # every RPC response matches the schema
        return response.status_code, body

    def call(self, method, params, request_id=1):
        request = {"jsonrpc": "2.0", "method": method, "params": params, "id": request_id}
        return self.post(request)

    def assert_result(self, reply, request_id):
        status, body = reply
        self.assertEqual(status, 200)
        self.assertEqual(body["jsonrpc"], "2.0")
        self.assertEqual(body["id"], request_id)
        self.assertNotIn("error", body)
        return body["result"]

    def assert_error(self, reply, request_id, code):
        status, body = reply
        self.assertEqual(status, 200)
        self.assertEqual(body["jsonrpc"], "2.0")
        self.assertEqual(body["id"], request_id)
        self.assertNotIn("result", body)
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)
        self.assert_no_internals(body)
        return body["error"]

    def assert_no_internals(self, body):
        text = json.dumps(body)
        for leak in ("Traceback", 'File "', ".py", "\\\\Users", "/Users/", "lambda3", "ENVcns", "D0V"):
            self.assertNotIn(leak, text)


# 1 -------------------------------------------------------------------------
class HealthTests(RpcTestCase):
    def test_health_returns_status_version_and_preserves_id(self):
        for request_id in ("health-1", 7, None):
            with self.subTest(id=request_id):
                result = self.assert_result(self.call("service.health", {}, request_id), request_id)
                self.assertEqual(result, {"status": "ok", "version": "1.0"})

    def test_health_rejects_unexpected_params(self):
        self.assert_error(self.call("service.health", {"x": 1}, "h"), "h", -32602)


# 2 and 9 -------------------------------------------------------------------
class TypecheckTests(RpcTestCase):
    def test_typecheck_valid_programs(self):
        cases = [
            ("1 + 2", "sint"),
            ("1 < 2", "bool"),
            ("(1, true)", "(sint, bool)"),
            ("list_cons(1, list_nil())", "List[sint]"),
            ("lam (x: sint) => x + 1", "sint -> sint"),
            (FACTORIAL, "sint"),
        ]
        for index, (source, expected) in enumerate(cases):
            with self.subTest(source=source):
                result = self.assert_result(self.call("lambda.typecheck", {"source": source}, index), index)
                self.assertEqual(result, {"type": expected})

    def test_typecheck_with_mylib_library(self):
        params = {"source": "list_length(list_cons(1, list_nil()))", "libraries": ["list"]}
        self.assertEqual(self.assert_result(self.call("lambda.typecheck", params, "lib"), "lib"),
                         {"type": "sint"})

    def test_typecheck_rejects_unbound_variable(self):
        error = self.assert_error(self.call("lambda.typecheck", {"source": "x + 1"}, "unbound"),
                                  "unbound", -32011)
        self.assertEqual(error["data"]["stage"], "typecheck")
        self.assertIn("unbound variable 'x'", error["data"]["message"])

    def test_library_function_is_unbound_without_library(self):
        self.assert_error(self.call("lambda.typecheck",
                                    {"source": "list_length(list_nil())"}, "nolib"), "nolib", -32011)


# 3 and 7 -------------------------------------------------------------------
class InterpretTests(RpcTestCase):
    def interpret(self, source, request_id="i", **extra):
        return self.assert_result(
            self.call("lambda.interpret", {"source": source, **extra}, request_id), request_id)

    def test_arithmetic(self):
        self.assertEqual(self.interpret("20 + 22"), {"type": "sint", "value": "42"})

    def test_factorial(self):
        self.assertEqual(self.interpret(FACTORIAL), {"type": "sint", "value": "720"})

    def test_tuple(self):
        self.assertEqual(self.interpret("(1, true, (2, false))"),
                         {"type": "(sint, bool, (sint, bool))", "value": "(1, true, (2, false))"})

    def test_collection_list(self):
        self.assertEqual(self.interpret("list_cons(1, list_cons(2, list_nil()))"),
                         {"type": "List[sint]", "value": "[1, 2]"})

    def test_collection_example_program(self):
        self.assertEqual(self.interpret(COLLECTION),
                         {"type": "(sint, sint, bool, sint)", "value": "(12, 3, false, 12)"})

    def test_collection_with_library(self):
        source = "list_reverse(list_cons(1, list_cons(2, list_cons(3, list_nil()))))"
        self.assertEqual(self.interpret(source, libraries=["list"]),
                         {"type": "List[sint]", "value": "[3, 2, 1]"})

    def test_function_values_are_formatted_without_closure_internals(self):
        lam = self.interpret("let f : sint -> sint = lam (x: sint) => x in f end")
        self.assertEqual(lam, {"type": "sint -> sint", "value": "<lam>"})
        fix = self.interpret("fix f(n: sint): sint => n")
        self.assertEqual(fix, {"type": "sint -> sint", "value": "<fix>"})

    def test_runtime_error_is_application_error(self):
        error = self.assert_error(self.call("lambda.interpret",
                                            {"source": "list_head(list_nil())"}, "rt"), "rt", -32013)
        self.assertEqual(error["data"]["exception"], "ValueError")

    def test_unbounded_recursion_is_resource_limit(self):
        source = "let f : sint -> sint = fix f(n: sint): sint => f(n) in f(0) end"
        self.assert_error(self.call("lambda.interpret", {"source": source}, "deep"), "deep", -32014)


# 4 -------------------------------------------------------------------------
class CompileTests(RpcTestCase):
    def test_python_and_javascript(self):
        markers = {"python": "def _lambda_main():", "javascript": "function _lambda_main()"}
        for target, marker in markers.items():
            with self.subTest(target=target):
                result = self.assert_result(
                    self.call("lambda.compile", {"source": FACTORIAL, "target": target}, target), target)
                self.assertEqual(result["target"], target)
                self.assertIsInstance(result["code"], str)
                self.assertIn(marker, result["code"])

    def test_code_is_returned_unchanged(self):
        L = self.service.L
        result = self.assert_result(
            self.call("lambda.compile", {"source": "1 + 2", "target": "python"}, 1), 1)
        self.assertEqual(result["code"], L.d0exp_compile(L.d0exp_parse("1 + 2")))

    def test_compile_still_typechecks_first(self):
        self.assert_error(self.call("lambda.compile", {"source": "1 + true", "target": "python"}, "c"),
                          "c", -32011)

    def test_bad_or_missing_target(self):
        for params in ({"source": "1"}, {"source": "1", "target": "ruby"},
                       {"source": "1", "target": "Python"}, {"source": "1", "target": 3}):
            with self.subTest(params=params):
                self.assert_error(self.call("lambda.compile", params, "t"), "t", -32602)


# 5 -------------------------------------------------------------------------
class LanguageErrorTests(RpcTestCase):
    def test_syntax_and_type_errors_have_distinct_codes(self):
        syntax = self.assert_error(self.call("lambda.typecheck", {"source": "if then"}, "s"), "s", -32010)
        self.assertEqual(syntax["data"]["stage"], "parse")
        self.assertEqual((syntax["data"]["line"], syntax["data"]["column"]), (1, 4))
        type_error = self.assert_error(self.call("lambda.typecheck", {"source": "1 + true"}, "t"), "t", -32011)
        self.assertEqual(type_error["data"]["stage"], "typecheck")

    def test_every_source_method_reports_language_errors(self):
        for method, extra in (("lambda.typecheck", {}), ("lambda.interpret", {}),
                              ("lambda.compile", {"target": "javascript"})):
            with self.subTest(method=method):
                self.assert_error(self.call(method, {"source": "let in", **extra}, 1), 1, -32010)
                self.assert_error(self.call(method, {"source": "if 1 then 2 else 3", **extra}, 2), 2, -32011)

    def test_syntax_error_positions_refer_to_user_source_with_libraries(self):
        error = self.assert_error(
            self.call("lambda.typecheck", {"source": "1 +\n  )", "libraries": ["list"]}, 1), 1, -32010)
        self.assertEqual((error["data"]["line"], error["data"]["column"]), (2, 3))


# 6 -------------------------------------------------------------------------
class EnvelopeAndParamsTests(RpcTestCase):
    def test_malformed_json_is_parse_error(self):
        for raw in (b'{"jsonrpc":', b"not json", b"\xff\xfe", b'{"a": NaN}'):
            with self.subTest(raw=raw):
                self.assert_error(self.post(raw=raw), None, -32700)

    def test_invalid_envelopes(self):
        bad = [
            {"jsonrpc": "1.0", "method": "service.health", "params": {}, "id": 1},
            {"method": "service.health", "params": {}, "id": 1},
            {"jsonrpc": "2.0", "method": 5, "params": {}, "id": 1},
            {"jsonrpc": "2.0", "params": {}, "id": 1},
            {"jsonrpc": "2.0", "method": "service.health", "params": "x", "id": 1},
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": {"x": 1}},
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": True},
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": 1, "extra": 0},
            "a string", 42, None,
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                self.assert_error(self.post(payload), None, -32600)

    def test_unknown_method(self):
        error = self.assert_error(self.call("lambda.lint", {}, "u"), "u", -32601)
        self.assertIn("lambda.interpret", error["data"]["available"])
        self.assert_error(self.call("Service.Health", {}, "case"), "case", -32601)

    def test_absent_or_wrongly_typed_params(self):
        no_params = {"jsonrpc": "2.0", "method": "lambda.typecheck", "id": "np"}
        self.assert_error(self.post(no_params), "np", -32602)
        by_position = {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": ["1 + 2"], "id": "arr"}
        self.assert_error(self.post(by_position), "arr", -32602)

    def test_invalid_source_values(self):
        for request_id, params in [("missing", {}), ("blank", {"source": "  \n\t"}),
                                   ("empty", {"source": ""}), ("number", {"source": 12}),
                                   ("null", {"source": None}), ("list", {"source": ["1"]}),
                                   ("extra", {"source": "1", "mode": "fast"}),
                                   ("badlib", {"source": "1", "libraries": ["nope"]}),
                                   ("duplib", {"source": "1", "libraries": ["list", "list"]})]:
            with self.subTest(params=params):
                self.assert_error(self.call("lambda.interpret", params, request_id), request_id, -32602)

    def test_oversized_source(self):
        limit = self.service.limits.max_source_bytes
        ok = "1" + " " * (limit - 1)  # exactly at the limit is accepted
        self.assert_result(self.call("lambda.typecheck", {"source": ok}, "at"), "at")
        error = self.assert_error(self.call("lambda.typecheck", {"source": ok + " "}, "over"), "over", -32602)
        self.assertEqual(error["data"]["maxSourceBytes"], limit)
        self.assertEqual(error["data"]["actualBytes"], limit + 1)

    def test_deeply_nested_source_is_resource_limit(self):
        source = "(" * 5000 + "1" + ")" * 5000
        self.assert_error(self.call("lambda.typecheck", {"source": source}, "nest"), "nest", -32014)


class TransportTests(RpcTestCase):
    def test_wrong_media_type_is_http_415(self):
        status, body = self.post({"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": 1},
                                  content_type="text/plain")
        self.assertEqual(status, 415)
        self.assertIsNone(body)

    def test_media_type_parameters_are_allowed(self):
        response = self.client.post("/rpc", data=json.dumps(
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": 1}),
            content_type="application/json; charset=utf-8")
        self.assertEqual(response.status_code, 200)

    def test_only_post_rpc_exists(self):
        self.assertEqual(self.client.get("/rpc").status_code, 405)
        self.assertEqual(self.client.post("/typecheck", json={}).status_code, 404)

    def test_body_too_large_is_http_413(self):
        big = b'"' + b"x" * (self.service.limits.max_body_bytes + 10) + b'"'
        self.assertEqual(self.post(raw=big)[0], 413)


# 8 -------------------------------------------------------------------------
class FailureInjectionTests(RpcTestCase):
    def client_for(self, **doubles):
        return create_app(LambdaService(Limits(), **doubles)).test_client()

    def test_backend_crash_is_internal_error_without_traceback(self):
        def broken_build(source, libraries):
            raise RuntimeError(r"secret detail C:\Users\someone\lambda3.py line 9")
        self.client = self.client_for(build=broken_build)
        with self.assertLogs("lambda_rpc", level="ERROR") as logs:
            error = self.assert_error(self.call("lambda.typecheck", {"source": "1"}, "boom"), "boom", -32603)
        self.assertEqual(error, {"code": -32603, "message": "Internal error"})
        self.assertIn("secret detail", "\n".join(logs.output))  # logged on the server only

    def test_interpreter_crash_is_internal_error(self):
        def broken_interpreter(source, libraries):
            raise MemoryError("worker exploded")
        self.client = self.client_for(interpreter=broken_interpreter)
        with self.assertLogs("lambda_rpc", level="ERROR"):
            self.assert_error(self.call("lambda.interpret", {"source": "1"}, 99), 99, -32603)

    def test_injected_timeout_is_reported(self):
        def timing_out(source, libraries):
            raise RpcError(EXECUTION_TIMEOUT, "Interpretation exceeded the 5 second limit and was stopped",
                           {"timeoutSeconds": 5})
        self.client = self.client_for(interpreter=timing_out)
        error = self.assert_error(self.call("lambda.interpret", {"source": "1"}, "slow"), "slow", -32012)
        self.assertEqual(error["data"]["timeoutSeconds"], 5)

    def test_real_worker_is_stopped_at_deadline(self):
        self.client = create_app(LambdaService(Limits(interpret_timeout=1.0))).test_client()
        error = self.assert_error(self.call("lambda.interpret", {"source": SLOW_FIB}, "fib"), "fib", -32012)
        self.assertEqual(error["data"]["timeoutSeconds"], 1.0)
        # The server keeps working after a timeout.
        self.assert_result(self.call("lambda.interpret", {"source": "6 * 7"}, "after"), "after")


class DispatchBoundaryTests(RpcTestCase):
    """A spy service shows exactly what the dispatcher passes to methods."""

    check_schema = False  # spy.echo is not part of the published contract

    def setUp(self):
        self.calls = []

        class SpyService:
            limits = Limits()

            def methods(spy):
                return {"spy.echo": lambda params: self.calls.append(params) or {"echo": params}}

        self.client = create_app(SpyService()).test_client()

    def test_params_are_passed_unchanged(self):
        status, body = self.post({"jsonrpc": "2.0", "method": "spy.echo", "params": {"a": [1, 2]}, "id": 3})
        self.assertEqual((status, body["result"], body["id"]), (200, {"echo": {"a": [1, 2]}}, 3))
        self.assertEqual(self.calls, [{"a": [1, 2]}])

    def test_invalid_envelope_never_reaches_a_method(self):
        self.post({"jsonrpc": "2.1", "method": "spy.echo", "params": {}, "id": 3})
        self.assertEqual(self.calls, [])

    def test_notifications_still_run(self):
        status, body = self.post({"jsonrpc": "2.0", "method": "spy.echo", "params": {"n": 1}})
        self.assertEqual((status, body), (204, None))
        self.assertEqual(self.calls, [{"n": 1}])


# 10 ------------------------------------------------------------------------
class BatchTests(RpcTestCase):
    def test_batch_preserves_ids_and_omits_notifications(self):
        batch = [
            {"jsonrpc": "2.0", "method": "lambda.interpret", "params": {"source": "6 * 7"}, "id": "answer"},
            {"jsonrpc": "2.0", "method": "service.health", "params": {}},            # notification
            {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "true"}, "id": 2},
            {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "1 + true"}, "id": 3},
            {"jsonrpc": "2.0", "method": "nope", "params": {}},                       # notification
        ]
        REQUEST_VALIDATOR.validate([r for r in batch if r["method"] != "nope"])
        status, body = self.post(batch)
        self.assertEqual(status, 200)
        by_id = {response["id"]: response for response in body}
        self.assertEqual(set(by_id), {"answer", 2, 3})
        self.assertEqual(by_id["answer"]["result"], {"type": "sint", "value": "42"})
        self.assertEqual(by_id[2]["result"], {"type": "bool"})
        self.assertEqual(by_id[3]["error"]["code"], -32011)

    def test_invalid_members_get_null_id_errors(self):
        batch = [
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": "ok"},
            "not-a-request",
            1,
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": [1]},
        ]
        status, body = self.post(batch)
        self.assertEqual(status, 200)
        self.assertEqual(len(body), 4)
        nulls = [r for r in body if r["id"] is None]
        self.assertEqual(len(nulls), 3)
        self.assertTrue(all(r["error"]["code"] == -32600 for r in nulls))

    def test_notification_only_batch_is_empty_204(self):
        response = self.client.post("/rpc", json=[
            {"jsonrpc": "2.0", "method": "service.health", "params": {}},
            {"jsonrpc": "2.0", "method": "lambda.typecheck", "params": {"source": "1 + 2"}},
        ])
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b"")

    def test_single_notification_is_empty_204(self):
        response = self.client.post("/rpc", json={"jsonrpc": "2.0", "method": "service.health", "params": {}})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b"")

    def test_failing_notification_is_still_silent(self):
        response = self.client.post("/rpc", json={"jsonrpc": "2.0", "method": "lambda.typecheck",
                                                  "params": {"source": "if then"}})
        self.assertEqual((response.status_code, response.data), (204, b""))

    def test_empty_batch_is_one_invalid_request_object(self):
        status, body = self.post([])
        self.assertIsInstance(body, dict)
        self.assert_error((status, body), None, -32600)

    def test_batch_size_limit(self):
        item = {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": 1}
        status, body = self.post([item] * (self.service.limits.max_batch_items + 1))
        self.assertIsInstance(body, dict)
        self.assert_error((status, body), None, -32600)


if __name__ == "__main__":
    unittest.main()
