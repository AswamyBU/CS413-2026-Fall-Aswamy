"""Construction checks for the generic option and linked-list types."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from basics0 import fnoptn, fnoptn_nil, fnoptn_cons
from basics0 import fnlist, fnlist_nil, fnlist_cons


class BasicsTests(unittest.TestCase):
    def test_options(self):
        self.assertIsInstance(fnoptn_nil[int](), fnoptn)
        value = fnoptn_cons[int](42)
        self.assertIsInstance(value, fnoptn)
        self.assertEqual(value.arg1, 42)

    def test_linked_list(self):
        tail = fnlist_cons[int](2, fnlist_nil[int]())
        values = fnlist_cons[int](1, tail)
        self.assertIsInstance(values, fnlist)
        self.assertEqual(values.arg1, 1)
        self.assertIs(values.arg2, tail)
        self.assertEqual(values.arg2.arg1, 2)
        self.assertIsInstance(values.arg2.arg2, fnlist_nil)


if __name__ == '__main__':
    unittest.main()
