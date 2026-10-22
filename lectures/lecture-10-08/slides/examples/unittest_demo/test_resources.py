import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from stack import announce, greeting
from service import status_code


class TestFiles(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)

    def test_text_round_trip(self):
        path = self.directory / "out.txt"
        path.write_text("hello", encoding="utf-8")
        self.assertEqual(path.read_text(encoding="utf-8"), "hello")


class TestResources(unittest.TestCase):
    def test_decimal_sum(self):
        self.assertAlmostEqual(0.1 + 0.2, 0.3, delta=1e-12)

    def test_announce(self):
        output = StringIO()
        with redirect_stdout(output):
            announce("Ada")
        self.assertEqual(output.getvalue(), "Hello, Ada!\n")

    def test_greeting(self):
        with patch.dict("os.environ", {"USER_NAME": "Ada"}):
            self.assertEqual(greeting(), "Hello, Ada")

    def test_default_greeting(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(greeting(), "Hello, guest")

    @patch("service.urlopen", autospec=True)
    def test_status_code(self, mock_open):
        mock_open.return_value.__enter__.return_value.status = 200
        self.assertEqual(status_code("https://example.org"), 200)
        mock_open.assert_called_once_with("https://example.org", timeout=2)


if __name__ == "__main__":
    unittest.main()
