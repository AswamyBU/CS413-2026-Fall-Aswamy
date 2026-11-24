"""Studio-level integration: real server, real LAMBDA3, real studio modules.

Starts the composed studio (database service + Assign07 LAMBDA3 service +
studio page) on an ephemeral port, then runs tests/js/integration.mjs with
Node. That script drives the studio's own storage adapter, LAMBDA3 client and
collection runner to save/reload a program, hit a stale-revision conflict,
build a collection, and run it with an expected value, an expected syntax
error, an expected type error, and two expected failures.
"""

import json
import shutil
import subprocess
import threading
import unittest
import urllib.request
from pathlib import Path

import logging

from werkzeug.serving import make_server

from studio_host import create_studio_app

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "Node.js is required for the studio integration test")
class StudioIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.getLogger("werkzeug").setLevel(logging.WARNING)  # quiet request log
        cls.server = make_server("127.0.0.1", 0, create_studio_app(), threaded=True)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_studio_page_and_modules_are_served(self):
        for path in ("/", "/app.js", "/storage.js", "/lambda.js", "/runner.js", "/drafts.js", "/studio.css"):
            with urllib.request.urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200, path)
                self.assertTrue(response.read(), path)
        with urllib.request.urlopen(self.base + "/") as response:
            page = response.read().decode()
        self.assertIn("everything is cleared when the service stops", page)

    def test_save_reload_and_run_collection_through_lambda3(self):
        out = subprocess.run([NODE, str(ROOT / "tests" / "js" / "integration.mjs"), self.base],
                             cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        report = json.loads(out.stdout)
        self.assertTrue(report["ok"])
        steps = {s["step"]: s for s in report["steps"]}
        self.assertEqual(steps["stale save refused"]["status"], 409)
        run = steps["run collection"]
        self.assertEqual((run["passed"], run["failed"]), (3, 2))
        by_name = {r["case"]: r for r in run["results"]}
        self.assertEqual(by_name["six factorial"]["outcome"], "value 720")
        self.assertTrue(by_name["missing operand"]["pass"])      # expected syntax error
        self.assertTrue(by_name["int plus bool"]["pass"])        # expected type error
        self.assertFalse(by_name["wrong expectation"]["pass"])
        self.assertFalse(by_name["runtime error is not a syntax error"]["pass"])


if __name__ == "__main__":
    unittest.main()
