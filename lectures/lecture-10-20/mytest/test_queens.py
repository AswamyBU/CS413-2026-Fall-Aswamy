"""Run the LAMBDA solver and independently validate its results."""
import sys
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import lambda2 as L
from basics0 import fnlist_cons, fnlist_nil


def unpack(value):
    if isinstance(value, L.D0Vint):
        return value.arg1
    if not isinstance(value, L.D0Vlist):
        raise AssertionError(f'Expected list or integer, got {value}')
    result = []
    items = value.arg1
    while isinstance(items, fnlist_cons):
        result.append(unpack(items.arg1))
        items = items.arg2
    if not isinstance(items, fnlist_nil):
        raise AssertionError('Malformed list')
    return result


class QueensTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / 'mylib/list.lam').read_text() + '\n' + (
            ROOT / 'mytest/queens.lam').read_text()
        declarations = L.d0cls_parse(source)
        # Return a closure so the library and eight-queen search run only once.
        output = io.StringIO()
        with redirect_stdout(output):
            cls.query = L.d0exp_evaluate(L.D0Elets(declarations,
                L.d0exp_parse('lam (n) => if n == 8 then queens_solutions else queens_solve(n)')))
        cls.output = output.getvalue()
        cls.env = L.ENVcns('solve', cls.query, L.ENVnil())

    def solve(self, n):
        return unpack(L.d0exp_evaluate(L.d0exp_parse(f'solve({n})'), self.env))

    def test_eight_queens(self):
        boards = self.solve(8)
        self.assertEqual(len(boards), 92)
        self.assertEqual(len({tuple(board) for board in boards}), 92)
        for board in boards:
            self.assertEqual(len(board), 8)
            self.assertEqual(set(board), set(range(8)))
            self.assertEqual(len({row - col for row, col in enumerate(board)}), 8)
            self.assertEqual(len({row + col for row, col in enumerate(board)}), 8)

    def test_small_boards(self):
        for n, count in [(0, 1), (1, 1), (2, 0), (3, 0), (4, 2)]:
            with self.subTest(n=n):
                self.assertEqual(len(self.solve(n)), count)
        self.assertEqual(self.solve(0), [[]])
        self.assertEqual({tuple(board) for board in self.solve(4)},
                         {(1, 3, 0, 2), (2, 0, 3, 1)})

    def test_printed_solutions(self):
        expected = ''.join(str(board) + '\n' for board in self.solve(8)) + '92\n'
        self.assertEqual(self.output, expected)


if __name__ == '__main__':
    unittest.main()
