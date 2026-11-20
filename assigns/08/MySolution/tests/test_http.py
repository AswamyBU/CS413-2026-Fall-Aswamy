"""End-to-end HTTP tests against a real server on an ephemeral port."""

import http.client
import json
import threading
import unittest

from queens.server import build_service, make_server
from queens.errors import STREAM_NOT_FOUND


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0, build_service("compiled"))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, method, path, body=None, content_type="application/json", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        all_headers = {"Content-Type": content_type} if content_type else {}
        all_headers.update(headers or {})
        conn.request(method, path, body=body, headers=all_headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, response.getheader("Content-Type"), data

    def call(self, method, params=None, id=1):
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": id}
        status, ctype, data = self.request("POST", "/rpc", json.dumps(payload))
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "application/json")
        return json.loads(data)

    def test_health(self):
        self.assertEqual(self.call("service.health")["result"], {"status": "ok", "version": "1.0"})

    def test_full_8x8_flow_open_to_done(self):
        sid = self.call("queens.open", {"size": 8})["result"]["stream_id"]
        solutions, events, calls = [], 0, 0
        while True:
            result = self.call("queens.next", {"stream_id": sid, "limit": 32}, id=calls)["result"]
            calls += 1
            self.assertLessEqual(len(result["events"]), 32)
            events += len(result["events"])
            solutions += [e["board"] for e in result["events"] if e["event"] == "solution"]
            if result["done"]:
                self.assertEqual(result["events"][-1], {"event": "done", "seq": events - 1})
                break
        self.assertEqual(len(solutions), 92)
        self.assertEqual(len({tuple(s) for s in solutions}), 92)
        self.assertEqual(solutions[0], [0, 4, 7, 5, 2, 6, 1, 3])
        self.assertEqual(solutions[-1], [7, 3, 0, 2, 5, 1, 6, 4])
        self.assertEqual(events, 33589)
        self.assertEqual(self.call("queens.next", {"stream_id": sid, "limit": 32})["result"],
                         {"events": [], "done": True})
        self.assertEqual(self.call("queens.close", {"stream_id": sid})["result"], {"closed": True})
        self.assertEqual(self.call("queens.next", {"stream_id": sid})["error"]["code"],
                         STREAM_NOT_FOUND)

    def test_notification_gets_204_and_empty_body(self):
        body = json.dumps({"jsonrpc": "2.0", "method": "service.health", "params": {}})
        status, _, data = self.request("POST", "/rpc", body)
        self.assertEqual((status, data), (204, b""))

    def test_jsonrpc_errors_use_http_200(self):
        status, _, data = self.request("POST", "/rpc", "{oops")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["error"]["code"], -32700)
        self.assertEqual(self.call("nope")["error"]["code"], -32601)

    def test_transport_errors(self):
        self.assertEqual(self.request("POST", "/rpc", "{}", content_type="text/plain")[0], 415)
        self.assertEqual(self.request("POST", "/rpc", "x" * (64 * 1024 + 1))[0], 413)
        self.assertEqual(self.request("GET", "/rpc")[0], 405)
        self.assertEqual(self.request("POST", "/other", "{}")[0], 404)
        self.assertEqual(self.request("GET", "/../queens/solver.py")[0], 404)

    def test_static_client_is_served(self):
        status, ctype, data = self.request("GET", "/", content_type=None)
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b'id="board"', data)
        for asset in ("/main.js", "/player.js", "/board.js", "/rpc.js", "/style.css"):
            self.assertEqual(self.request("GET", asset, content_type=None)[0], 200, asset)

    def test_concurrent_clients_on_one_stream_get_disjoint_events(self):
        sid = self.call("queens.open", {"size": 8})["result"]["stream_id"]
        seqs, lock = [], threading.Lock()

        def worker():
            for _ in range(5):
                events = self.call("queens.next", {"stream_id": sid, "limit": 10})["result"]["events"]
                with lock:
                    seqs.extend(e["seq"] for e in events)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(seqs), list(range(200)))


if __name__ == "__main__":
    unittest.main()
