import unittest
from expr import free_vars


class TestFreeVars(unittest.TestCase):
    def test_cases(self):
        cases = [
            (("var", "x"), {"x"}),
            (("lam", "x", ("var", "x")), set()),
            (("lam", "x", ("var", "y")), {"y"}),
            (("app", ("var", "x"), ("var", "y")), {"x", "y"}),
            (("lam", "x", ("app", ("var", "x"),
                ("lam", "y", ("var", "x")))), set()),
        ]
        for expr, expected in cases:
            with self.subTest(expr=expr):
                self.assertEqual(free_vars(expr), expected)


if __name__ == "__main__":
    unittest.main()
