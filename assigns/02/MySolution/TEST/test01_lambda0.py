"""Examples for call-by-value evaluation.

Run with: python3 TEST/test01_lambda0.py
Requires Python 3.12 or later, like lambda0.py.
"""

import sys
import unittest
from pathlib import Path

# Allow this file to run directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0, T0Mop1, T0Mop2,
    t0erm_cbv_evaluate0,
)


class TestCBVEvaluate(unittest.TestCase):
    def test_values(self):
        # A lambda is a value: its body is not evaluated.
        values = [
            T0Mint(42), T0Mbtf(True), T0Mbtf(False), T0Mstr("hello"),
            T0Mlam("x", T0Mop2("/", T0Mint(1), T0Mint(0))),
        ]
        for value in values:
            with self.subTest(value=value):
                self.assertIs(t0erm_cbv_evaluate0(value), value)

    def test_unary_arithmetic(self):
        for op, operand, expected in [
            ("+", 7, 7), ("+", -7, -7),
            ("-", 7, -7), ("-", -7, 7), ("-", 0, 0),
        ]:
            with self.subTest(op=op, operand=operand):
                term = T0Mop1(op, T0Mint(operand))
                self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(expected))

    def test_binary_arithmetic(self):
        for op, left, right, expected in [
            ("+", 7, 3, 10), ("-", 3, 7, -4), ("*", -7, 3, -21),
            ("/", 7, 3, 2), ("%", 7, 3, 1),
            # Division rounds down; modulo has the divisor's sign.
            ("/", -7, 3, -3), ("%", -7, 3, 2),
            ("/", 7, -3, -3), ("%", 7, -3, -2),
        ]:
            with self.subTest(op=op, left=left, right=right):
                term = T0Mop2(op, T0Mint(left), T0Mint(right))
                self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(expected))

    def test_nested_arithmetic(self):
        # -(2 + 3) * (10 - 4) = -30
        term = T0Mop2(
            "*",
            T0Mop1("-", T0Mop2("+", T0Mint(2), T0Mint(3))),
            T0Mop2("-", T0Mint(10), T0Mint(4)),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(-30))

    def test_application(self):
        # (lambda x: x + 1)(2 * 3) = 7
        term = T0Mapp(
            T0Mlam("x", T0Mop2("+", T0Mvar("x"), T0Mint(1))),
            T0Mop2("*", T0Mint(2), T0Mint(3)),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(7))

    def test_nested_application(self):
        # The outer application evaluates its function expression first.
        term = T0Mapp(
            T0Mapp(T0Mlam("x", T0Mlam("y", T0Mvar("x"))), T0Mint(7)),
            T0Mint(9),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(7))
        # An inner binding of x shadows the outer binding.
        term = T0Mapp(
            T0Mapp(T0Mlam("x", T0Mlam("x", T0Mvar("x"))), T0Mint(7)),
            T0Mint(9),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(9))

    def test_application_evaluates_unused_argument(self):
        term = T0Mapp(
            T0Mlam("x", T0Mint(42)),
            T0Mop2("/", T0Mint(1), T0Mint(0)),
        )
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_application_evaluates_function_first(self):
        term = T0Mapp(
            T0Mop2("/", T0Mint(1), T0Mint(0)),
            T0Mop1("-", T0Mstr("bad")),
        )
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_fix_application(self):
        identity = T0Mfix("f", "x", T0Mvar("x"))
        term = T0Mapp(identity, T0Mop2("+", T0Mint(3), T0Mint(4)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(7))

    def test_fix_recursion(self):
        # f(flag) = if flag then 1 + f(false) else 0.
        function = T0Mfix("f", "flag", T0Mif0(
            T0Mvar("flag"),
            T0Mop2("+", T0Mint(1), T0Mapp(T0Mvar("f"), T0Mbtf(False))),
            T0Mint(0),
        ))
        for flag, expected in [(False, 0), (True, 1)]:
            with self.subTest(flag=flag):
                self.assertEqual(
                    t0erm_cbv_evaluate0(T0Mapp(function, T0Mbtf(flag))),
                    T0Mint(expected),
                )

    def test_fix_fibonacci(self):
        # fib(0) = 0, fib(1) = 1, fib(n) = fib(n-1) + fib(n-2).
        n = T0Mvar("n")
        fib = T0Mfix("fib", "n", T0Mif0(
            T0Mop2("<=", n, T0Mint(1)),
            n,
            T0Mop2("+",
                T0Mapp(T0Mvar("fib"), T0Mop2("-", n, T0Mint(1))),
                T0Mapp(T0Mvar("fib"), T0Mop2("-", n, T0Mint(2))),
            ),
        ))
        for argument, expected in [(0, 0), (1, 1), (2, 1), (3, 2), (5, 5), (10, 55)]:
            with self.subTest(n=argument):
                term = T0Mapp(fib, T0Mint(argument))
                self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(expected))

    def test_integer_less_equal(self):
        for left, right, expected in [(0, 1, True), (1, 1, True), (2, 1, False), (-2, -1, True)]:
            with self.subTest(left=left, right=right):
                term = T0Mop2("<=", T0Mint(left), T0Mint(right))
                self.assertEqual(t0erm_cbv_evaluate0(term), T0Mbtf(expected))

    def test_fix_evaluates_unused_argument(self):
        term = T0Mapp(
            T0Mfix("f", "x", T0Mint(42)),
            T0Mop2("/", T0Mint(1), T0Mint(0)),
        )
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_fix_preserves_inner_binding(self):
        function = T0Mfix("f", "x", T0Mlam("f", T0Mvar("f")))
        term = T0Mapp(T0Mapp(function, T0Mint(7)), T0Mint(9))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(9))

    def test_application_requires_lambda(self):
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(T0Mapp(T0Mint(1), T0Mint(2)))

    def test_conditional(self):
        bad_branch = T0Mop2("/", T0Mint(1), T0Mint(0))
        good_branch = T0Mop2("+", T0Mint(2), T0Mint(3))
        for condition in (True, False):
            # Evaluate the condition expression and only the selected branch.
            test = T0Mapp(T0Mlam("x", T0Mvar("x")), T0Mbtf(condition))
            then, otherwise = (good_branch, bad_branch) if condition else (bad_branch, good_branch)
            with self.subTest(condition=condition):
                term = T0Mif0(test, then, otherwise)
                self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(5))

    def test_conditional_requires_boolean(self):
        for condition in (T0Mint(0), T0Mstr("true"), T0Mlam("x", T0Mvar("x"))):
            with self.subTest(condition=condition):
                with self.assertRaises(TypeError):
                    t0erm_cbv_evaluate0(T0Mif0(condition, T0Mint(1), T0Mint(2)))

    def test_noninteger_operands(self):
        for value in [T0Mbtf(True), T0Mstr("3"), T0Mlam("x", T0Mvar("x"))]:
            for op in ("+", "-"):
                with self.subTest(op=op, value=value):
                    with self.assertRaises(TypeError):
                        t0erm_cbv_evaluate0(T0Mop1(op, value))
            for op in ("+", "-", "*", "/", "%", "<="):
                for left, right in [(value, T0Mint(2)), (T0Mint(2), value)]:
                    with self.subTest(op=op, left=left, right=right):
                        with self.assertRaises(TypeError):
                            t0erm_cbv_evaluate0(T0Mop2(op, left, right))

    def test_zero_divisors(self):
        for op in ("/", "%"):
            with self.subTest(op=op):
                with self.assertRaises(ZeroDivisionError):
                    t0erm_cbv_evaluate0(T0Mop2(op, T0Mint(1), T0Mint(0)))

    def test_unsupported_operators(self):
        for term in [
            T0Mop1("unknown", T0Mint(1)),
            T0Mop2("unknown", T0Mint(1), T0Mint(2)),
        ]:
            with self.subTest(term=term):
                with self.assertRaises(TypeError):
                    t0erm_cbv_evaluate0(term)

    def test_left_operand_evaluated_first(self):
        # The left operand's division error occurs before the right's type error.
        term = T0Mop2(
            "+", T0Mop2("/", T0Mint(1), T0Mint(0)),
            T0Mop1("-", T0Mstr("bad")),
        )
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)


def church_numeral(n):
    """Build the Church numeral lambda f. lambda x. f^n(x)."""
    body = T0Mvar("x")
    for _ in range(n):
        body = T0Mapp(T0Mvar("f"), body)
    return T0Mlam("f", T0Mlam("x", body))


def church_to_integer(term):
    """Observe a Church numeral by applying increment and zero."""
    increment = T0Mlam("x", T0Mop2("+", T0Mvar("x"), T0Mint(1)))
    return t0erm_cbv_evaluate0(T0Mapp(T0Mapp(term, increment), T0Mint(0)))


# succ = lambda n. lambda f. lambda x. f (n f x)
CHURCH_SUCC = T0Mlam("n", T0Mlam("f", T0Mlam("x",
    T0Mapp(T0Mvar("f"),
        T0Mapp(T0Mapp(T0Mvar("n"), T0Mvar("f")), T0Mvar("x"))))))

# add = lambda m. lambda n. lambda f. lambda x. m f (n f x)
CHURCH_ADD = T0Mlam("m", T0Mlam("n", T0Mlam("f", T0Mlam("x",
    T0Mapp(T0Mapp(T0Mvar("m"), T0Mvar("f")),
        T0Mapp(T0Mapp(T0Mvar("n"), T0Mvar("f")), T0Mvar("x")))))))

# mul = lambda m. lambda n. lambda f. m (n f)
CHURCH_MUL = T0Mlam("m", T0Mlam("n", T0Mlam("f",
    T0Mapp(T0Mvar("m"), T0Mapp(T0Mvar("n"), T0Mvar("f"))))))


class TestChurchNumerals(unittest.TestCase):
    def test_conversion(self):
        for n in range(6):
            with self.subTest(n=n):
                self.assertEqual(church_to_integer(church_numeral(n)), T0Mint(n))

    def test_successor(self):
        for n in (0, 1, 4):
            with self.subTest(n=n):
                term = T0Mapp(CHURCH_SUCC, church_numeral(n))
                self.assertEqual(church_to_integer(term), T0Mint(n + 1))

    def test_addition(self):
        for left, right, expected in [(0, 0, 0), (0, 3, 3), (3, 0, 3), (2, 3, 5)]:
            with self.subTest(left=left, right=right):
                term = T0Mapp(T0Mapp(CHURCH_ADD, church_numeral(left)), church_numeral(right))
                self.assertEqual(church_to_integer(term), T0Mint(expected))

    def test_multiplication(self):
        for left, right, expected in [(0, 3, 0), (3, 0, 0), (1, 3, 3), (3, 1, 3), (2, 3, 6)]:
            with self.subTest(left=left, right=right):
                term = T0Mapp(T0Mapp(CHURCH_MUL, church_numeral(left)), church_numeral(right))
                self.assertEqual(church_to_integer(term), T0Mint(expected))

    def test_composed_arithmetic(self):
        # succ(2 + 3) * 2 = 12, using only Church operations before conversion.
        total = T0Mapp(T0Mapp(CHURCH_ADD, church_numeral(2)), church_numeral(3))
        successor = T0Mapp(CHURCH_SUCC, total)
        product = T0Mapp(T0Mapp(CHURCH_MUL, successor), church_numeral(2))
        self.assertEqual(church_to_integer(product), T0Mint(12))

    def test_iteration_with_different_function_and_seed(self):
        # Church three applies doubling three times: 1 -> 2 -> 4 -> 8.
        double = T0Mlam("x", T0Mop2("*", T0Mvar("x"), T0Mint(2)))
        term = T0Mapp(T0Mapp(church_numeral(3), double), T0Mint(1))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(8))


if __name__ == "__main__":
    unittest.main(verbosity=2)
