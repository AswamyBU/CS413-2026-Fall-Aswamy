import unittest
from stack import Stack


class TestStack(unittest.TestCase):
    def setUp(self):
        self.stack = Stack()

    def test_pop_returns_last_pushed(self):
        stack = Stack()
        stack.push("x")
        stack.push("y")
        self.assertEqual(stack.pop(), "y")

    def test_round_trip(self):
        self.stack.push(7)
        self.assertEqual(self.stack.pop(), 7)

    def test_empty_pop(self):
        with self.assertRaisesRegex(IndexError, "empty stack"):
            self.stack.pop()

    def test_lifo_cases(self):
        for values in ([], [7], [2, 5, 2]):
            with self.subTest(values=values):
                stack = Stack()
                for value in values:
                    stack.push(value)
                actual = [stack.pop() for _ in values]
                self.assertEqual(actual, list(reversed(values)))

    def test_interleaved_operations(self):
        self.stack.push("x")
        self.stack.push("y")
        self.assertEqual(self.stack.pop(), "y")
        self.stack.push("z")
        self.assertEqual(self.stack.pop(), "z")
        self.assertEqual(self.stack.pop(), "x")
        with self.assertRaises(IndexError):
            self.stack.pop()

    def test_list_behavior(self):
        a = [1, 2]
        b = [1, 2]
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertCountEqual([1, 2, 2], [2, 1, 2])


if __name__ == "__main__":
    unittest.main()
