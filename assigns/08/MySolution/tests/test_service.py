"""Stream table, RPC methods, and JSON-RPC envelope tests (no HTTP)."""

import json
import unittest

from queens.errors import (INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST,
                           METHOD_NOT_FOUND, PARSE_ERROR, STREAM_NOT_FOUND,
                           TOO_MANY_STREAMS)
from queens.jsonrpc import Dispatcher
from queens.service import QueensService
from queens.solver import CompiledBackend
from queens.streams import StreamTable


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(ttl=300.0, max_streams=64):
    clock = FakeClock()
    backend = CompiledBackend()
    table = StreamTable(backend, ttl_seconds=ttl, max_streams=max_streams, clock=clock)
    service = QueensService(table)
    return service, Dispatcher(service.methods()), clock, backend


def rpc(dispatcher, method, params=None, id=1, **extra):
    request = {"jsonrpc": "2.0", "method": method, "id": id, **extra}
    if params is not None:
        request["params"] = params
    return dispatcher.handle_body(json.dumps(request).encode())


class StreamLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.service, self.d, self.clock, self.backend = make()

    def open(self, size=4):
        return rpc(self.d, "queens.open", {"size": size})["result"]["stream_id"]

    def test_open_does_not_force(self):
        result = rpc(self.d, "queens.open", {"size": 10})["result"]
        self.assertEqual(result["size"], 10)
        self.assertEqual(len(result["stream_id"]), 36)  # uuid4
        self.assertEqual(self.backend.thunks_forced, 0)

    def test_next_forces_only_what_is_requested(self):
        sid = self.open(10)
        result = rpc(self.d, "queens.next", {"stream_id": sid, "limit": 3})["result"]
        self.assertEqual(len(result["events"]), 3)
        self.assertEqual(self.backend.thunks_forced, 6)

    def test_limits_1_and_32(self):
        sid = self.open(8)
        one = rpc(self.d, "queens.next", {"stream_id": sid, "limit": 1})["result"]
        self.assertEqual(len(one["events"]), 1)
        many = rpc(self.d, "queens.next", {"stream_id": sid, "limit": 32})["result"]
        self.assertEqual(len(many["events"]), 32)
        self.assertEqual([e["seq"] for e in many["events"]], list(range(1, 33)))
        default = rpc(self.d, "queens.next", {"stream_id": sid})["result"]
        self.assertEqual(len(default["events"]), 1)

    def test_exhaustion_repeated_next_and_release(self):
        sid = self.open(4)
        events = []
        while True:
            result = rpc(self.d, "queens.next", {"stream_id": sid, "limit": 32})["result"]
            self.assertLessEqual(len(result["events"]), 32)
            events += result["events"]
            if result["done"]:
                break
        self.assertEqual(events[-1], {"event": "done", "seq": len(events) - 1})
        self.assertEqual([e["number"] for e in events if e["event"] == "solution"], [1, 2])
        # Solver state is released as soon as `done` is delivered.
        self.assertTrue(self.service.table.is_exhausted(sid))
        for _ in range(2):
            self.assertEqual(rpc(self.d, "queens.next", {"stream_id": sid, "limit": 5})["result"],
                             {"events": [], "done": True})

    def test_done_response_is_short_when_stream_ends(self):
        sid = self.open(4)
        total = 0
        while True:
            result = rpc(self.d, "queens.next", {"stream_id": sid, "limit": 7})["result"]
            total += len(result["events"])
            if result["done"]:
                self.assertLessEqual(len(result["events"]), 7)
                self.assertEqual(result["events"][-1]["event"], "done")
                break
            self.assertEqual(len(result["events"]), 7)
        self.assertEqual(total, 60 + 16 + 44 + 16 + 2 + 1)

    def test_close_then_unknown(self):
        sid = self.open()
        self.assertEqual(rpc(self.d, "queens.close", {"stream_id": sid})["result"], {"closed": True})
        self.assertNotIn(sid, self.service.table)
        for method, params in (("queens.next", {"stream_id": sid}), ("queens.close", {"stream_id": sid})):
            error = rpc(self.d, method, params)["error"]
            self.assertEqual(error["code"], STREAM_NOT_FOUND)

    def test_unknown_id(self):
        error = rpc(self.d, "queens.next", {"stream_id": "not-a-stream"})["error"]
        self.assertEqual(error["code"], STREAM_NOT_FOUND)
        self.assertEqual(error["data"], {"stream_id": "not-a-stream"})

    def test_expiration_after_idle_ttl(self):
        sid = self.open()
        self.clock.now += 299
        self.assertIn("result", rpc(self.d, "queens.next", {"stream_id": sid}))  # refreshes
        self.clock.now += 299
        self.assertIn("result", rpc(self.d, "queens.next", {"stream_id": sid}))
        self.clock.now += 301
        self.assertEqual(rpc(self.d, "queens.next", {"stream_id": sid})["error"]["code"],
                         STREAM_NOT_FOUND)

    def test_cleanup_sweeps_idle_and_exhausted_records(self):
        a, b = self.open(), self.open()
        while not rpc(self.d, "queens.next", {"stream_id": b, "limit": 32})["result"]["done"]:
            pass
        self.assertEqual(len(self.service.table), 2)
        self.clock.now += 301
        self.assertEqual(self.service.table.sweep(), 2)
        self.assertEqual(len(self.service.table), 0)
        self.assertNotIn(a, self.service.table)

    def test_open_stream_cap(self):
        service, d, clock, _ = make(max_streams=2)
        rpc(d, "queens.open", {"size": 4})
        rpc(d, "queens.open", {"size": 4})
        error = rpc(d, "queens.open", {"size": 4})["error"]
        self.assertEqual(error["code"], TOO_MANY_STREAMS)
        clock.now += 1000  # idle streams expire and free their slots
        self.assertIn("result", rpc(d, "queens.open", {"size": 4}))

    def test_streams_are_independent(self):
        a, b = self.open(8), self.open(8)
        ea = rpc(self.d, "queens.next", {"stream_id": a, "limit": 10})["result"]["events"]
        eb = rpc(self.d, "queens.next", {"stream_id": b, "limit": 4})["result"]["events"]
        self.assertEqual(ea[:4], eb)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.service, self.d, _, self.backend = make()

    def assertInvalidParams(self, method, params):
        response = rpc(self.d, method, params, id="v")
        self.assertEqual(response["error"]["code"], INVALID_PARAMS, (method, params))
        self.assertEqual(response["id"], "v")

    def test_health(self):
        self.assertEqual(rpc(self.d, "service.health", {})["result"], {"status": "ok", "version": "1.0"})
        self.assertEqual(rpc(self.d, "service.health")["result"]["status"], "ok")  # params omitted
        self.assertInvalidParams("service.health", {"x": 1})

    def test_open_sizes(self):
        for size in (4, 10):
            self.assertIn("result", rpc(self.d, "queens.open", {"size": size}))
        for size in (3, 11, 0, -8, 8.0, 8.5, "8", True, None, [8]):
            self.assertInvalidParams("queens.open", {"size": size})
        self.assertInvalidParams("queens.open", {})
        self.assertInvalidParams("queens.open", {"size": 8, "extra": 1})
        # Nothing was allocated by any rejected call.
        self.assertEqual(len(self.service.table), 2)

    def test_next_params(self):
        sid = rpc(self.d, "queens.open", {"size": 8})["result"]["stream_id"]
        for limit in (0, 33, -1, 1.5, "1", True, None):
            self.assertInvalidParams("queens.next", {"stream_id": sid, "limit": limit})
        for stream_id in (1, None, "", ["x"], "x" * 65):
            self.assertInvalidParams("queens.next", {"stream_id": stream_id})
        self.assertInvalidParams("queens.next", {"limit": 1})
        self.assertInvalidParams("queens.next", {"stream_id": sid, "limit": 1, "size": 8})
        self.assertEqual(self.backend.thunks_forced, 0)  # invalid calls forced nothing

    def test_positional_params_rejected(self):
        self.assertInvalidParams("queens.open", [8])


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        _, self.d, _, _ = make()

    def test_ids_preserved(self):
        for request_id in (7, "abc", None, 2.5):
            self.assertEqual(rpc(self.d, "service.health", {}, id=request_id)["id"], request_id)
        self.assertEqual(rpc(self.d, "nope", {}, id="keep")["id"], "keep")

    def test_parse_error(self):
        response = self.d.handle_body(b"{not json")
        self.assertEqual(response["error"]["code"], PARSE_ERROR)
        self.assertIsNone(response["id"])
        self.assertEqual(self.d.handle_body(b'{"x": NaN}')["error"]["code"], PARSE_ERROR)

    def test_malformed_envelopes(self):
        bad = [
            42, "str", {},
            {"jsonrpc": "1.0", "method": "service.health", "id": 1},
            {"method": "service.health", "id": 1},
            {"jsonrpc": "2.0", "id": 1},
            {"jsonrpc": "2.0", "method": 5, "id": 1},
            {"jsonrpc": "2.0", "method": "", "id": 1},
            {"jsonrpc": "2.0", "method": "service.health", "params": 3, "id": 1},
            {"jsonrpc": "2.0", "method": "service.health", "id": {"a": 1}},
            {"jsonrpc": "2.0", "method": "service.health", "id": True},
            {"jsonrpc": "2.0", "method": "service.health", "id": 1, "extra": 1},
        ]
        for request in bad:
            response = self.d.handle_body(json.dumps(request).encode())
            self.assertEqual(response["error"]["code"], INVALID_REQUEST, request)
            self.assertIsNone(response["id"])

    def test_batch_not_supported(self):
        body = json.dumps([{"jsonrpc": "2.0", "method": "service.health", "id": 1}]).encode()
        self.assertEqual(self.d.handle_body(body)["error"]["code"], INVALID_REQUEST)

    def test_unknown_method(self):
        for name in ("queens.solveAll", "eval", "__init__", "service.health "):
            error = rpc(self.d, name, {})["error"]
            self.assertEqual(error["code"], METHOD_NOT_FOUND)

    def test_notifications_get_no_response(self):
        body = json.dumps({"jsonrpc": "2.0", "method": "service.health", "params": {}}).encode()
        self.assertIsNone(self.d.handle_body(body))
        # Even a failing notification is silent.
        body = json.dumps({"jsonrpc": "2.0", "method": "nope"}).encode()
        self.assertIsNone(self.d.handle_body(body))

    def test_notification_is_executed(self):
        service, d, _, _ = make()
        sid = rpc(d, "queens.open", {"size": 4})["result"]["stream_id"]
        d.handle_body(json.dumps({"jsonrpc": "2.0", "method": "queens.close",
                                  "params": {"stream_id": sid}}).encode())
        self.assertNotIn(sid, service.table)

    def test_internal_error_hides_details(self):
        def boom(params):
            raise RuntimeError("secret C:\\path\\lambda3.py <fix>")
        d = Dispatcher({"boom": boom})
        with self.assertLogs("queens.rpc", "ERROR"):
            response = rpc(d, "boom", {}, id=9)
        self.assertEqual(response, {"jsonrpc": "2.0", "id": 9,
                                    "error": {"code": INTERNAL_ERROR, "message": "Internal error"}})

    def test_responses_never_contain_lambda_values(self):
        service, d, _, _ = make()
        sid = rpc(d, "queens.open", {"size": 6})["result"]["stream_id"]
        text = json.dumps(rpc(d, "queens.next", {"stream_id": sid, "limit": 32}))
        for leak in ("lazy", "D0V", "lam", "ENV", "Traceback"):
            self.assertNotIn(leak, text)


if __name__ == "__main__":
    unittest.main()
