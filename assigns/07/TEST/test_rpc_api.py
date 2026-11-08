"""Black-box contract tests for the Assign07 JSON-RPC service.

Start the service before running this suite. Set LAMBDA_RPC_URL to override
the default endpoint (http://127.0.0.1:8000/rpc).
"""

import json
import os
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RPC_URL = os.environ.get("LAMBDA_RPC_URL", "http://127.0.0.1:8000/rpc")
TIMEOUT_SECONDS = 10


def post_rpc(payload, *, raw_body=None):
    """Return (status, decoded_json_or_none) for one HTTP POST to /rpc."""
    if raw_body is None:
        body = json.dumps(payload).encode("utf-8")
    else:
        body = raw_body
    request = Request(
        RPC_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = urlopen(request, timeout=TIMEOUT_SECONDS)
    except HTTPError as error:
        response = error
    except URLError as error:
        raise AssertionError(
            f"Could not reach JSON-RPC service at {RPC_URL}: {error}"
        ) from error

    with response:
        response_body = response.read()
        if not response_body:
            decoded = None
        else:
            try:
                decoded = json.loads(response_body)
            except json.JSONDecodeError as error:
                raise AssertionError(
                    f"Service returned non-JSON response: {response_body[:200]!r}"
                ) from error
        return response.status, decoded


def call(method, params, request_id=1):
    return post_rpc({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id,
    })


class JsonRpcContractTests(unittest.TestCase):
    def assert_success(self, response, request_id):
        status, body = response
        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)
        self.assertEqual(body.get("jsonrpc"), "2.0")
        self.assertEqual(body.get("id"), request_id)
        self.assertIn("result", body)
        self.assertNotIn("error", body)
        return body["result"]

    def assert_rpc_error(self, response, request_id, expected_code):
        status, body = response
        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)
        self.assertEqual(body.get("jsonrpc"), "2.0")
        self.assertEqual(body.get("id"), request_id)
        self.assertIn("error", body)
        self.assertNotIn("result", body)
        self.assertEqual(body["error"].get("code"), expected_code)
        self.assertIsInstance(body["error"].get("message"), str)
        return body["error"]

    def test_health(self):
        result = self.assert_success(call("service.health", {}, "health-1"), "health-1")
        self.assertEqual(result, {"status": "ok", "version": "1.0"})

    def test_typecheck_arithmetic(self):
        result = self.assert_success(
            call("lambda.typecheck", {"source": "1 + 2"}, 2), 2
        )
        self.assertEqual(result, {"type": "sint"})

    def test_interpret_arithmetic(self):
        result = self.assert_success(
            call("lambda.interpret", {"source": "20 + 22"}, 3), 3
        )
        self.assertEqual(result, {"type": "sint", "value": "42"})

    def test_interpret_tuple(self):
        result = self.assert_success(
            call("lambda.interpret", {"source": "(1, true)"}, 4), 4
        )
        self.assertEqual(result, {"type": "(sint, bool)", "value": "(1, true)"})

    def test_interpret_list(self):
        result = self.assert_success(
            call(
                "lambda.interpret",
                {"source": "list_cons(1, list_cons(2, list_nil()))"},
                41,
            ),
            41,
        )
        self.assertEqual(result, {"type": "List[sint]", "value": "[1, 2]"})

    def test_interpret_function_formats_closure(self):
        source = "let f : sint -> sint = lam (x: sint) => x in f end"
        result = self.assert_success(
            call("lambda.interpret", {"source": source}, 5), 5
        )
        self.assertEqual(result, {"type": "sint -> sint", "value": "<lam>"})
        self.assertNotIn("environment", result["value"].lower())

    def test_compile_python_and_javascript(self):
        for target in ("python", "javascript"):
            with self.subTest(target=target):
                result = self.assert_success(
                    call("lambda.compile", {"source": "1 + 2", "target": target}, target),
                    target,
                )
                self.assertEqual(result.get("target"), target)
                self.assertIsInstance(result.get("code"), str)
                self.assertTrue(result["code"].strip())

    def test_language_syntax_and_type_errors_are_distinct(self):
        syntax = self.assert_rpc_error(
            call("lambda.typecheck", {"source": "if then"}, "syntax"),
            "syntax",
            -32010,
        )
        type_error = self.assert_rpc_error(
            call("lambda.typecheck", {"source": "1 + true"}, "type"),
            "type",
            -32011,
        )
        self.assertNotEqual(syntax["code"], type_error["code"])

    def test_invalid_params_and_unknown_method(self):
        self.assert_rpc_error(
            call("lambda.interpret", {"source": "   "}, "blank"),
            "blank",
            -32602,
        )
        self.assert_rpc_error(
            call("lambda.interpret", {"source": 12}, "wrong-type"),
            "wrong-type",
            -32602,
        )
        self.assert_rpc_error(
            call("lambda.interpret", {}, "missing-source"),
            "missing-source",
            -32602,
        )
        self.assert_rpc_error(
            call(
                "lambda.compile",
                {"source": "1 + 2", "target": "ruby"},
                "bad-target",
            ),
            "bad-target",
            -32602,
        )
        self.assert_rpc_error(
            call("does.not.exist", {}, "unknown"), "unknown", -32601
        )

    def test_malformed_json_returns_parse_error(self):
        status, body = post_rpc(None, raw_body=b'{"jsonrpc":')
        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)
        self.assertEqual(body.get("jsonrpc"), "2.0")
        self.assertIsNone(body.get("id"))
        self.assertEqual(body.get("error", {}).get("code"), -32700)

    def test_batch_matches_by_id_and_omits_notification(self):
        payload = [
            {"jsonrpc": "2.0", "method": "lambda.interpret", "params": {"source": "6 * 7"}, "id": "answer"},
            {"jsonrpc": "2.0", "method": "service.health", "params": {}},
        ]
        status, body = post_rpc(payload)
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0].get("id"), "answer")
        self.assertEqual(body[0].get("result"), {"type": "sint", "value": "42"})

    def test_notification_only_batch_has_no_response(self):
        payload = [
            {"jsonrpc": "2.0", "method": "service.health", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "lambda.typecheck",
                "params": {"source": "1 + 2"},
            },
        ]
        status, body = post_rpc(payload)
        self.assertEqual(status, 204)
        self.assertIsNone(body)

    def test_notification_has_no_response(self):
        notification = {
            "jsonrpc": "2.0",
            "method": "service.health",
            "params": {},
        }
        status, body = post_rpc(notification)
        self.assertEqual(status, 204)
        self.assertIsNone(body)

    def test_invalid_request_and_empty_batch(self):
        for payload in ({"jsonrpc": "1.0", "method": "service.health", "id": 1}, []):
            with self.subTest(payload=payload):
                status, body = post_rpc(payload)
                self.assertEqual(status, 200)
                self.assertEqual(body.get("jsonrpc"), "2.0")
                self.assertIsNone(body.get("id"))
                self.assertEqual(body.get("error", {}).get("code"), -32600)

    def test_malformed_batch_member_gets_null_id_error(self):
        payload = [
            {"jsonrpc": "2.0", "method": "service.health", "params": {}, "id": "ok"},
            "not-a-request-object",
        ]
        status, body = post_rpc(payload)
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 2)
        by_id = {response.get("id"): response for response in body}
        self.assertEqual(by_id["ok"].get("result"), {"status": "ok", "version": "1.0"})
        self.assertEqual(by_id[None].get("error", {}).get("code"), -32600)


if __name__ == "__main__":
    unittest.main()
