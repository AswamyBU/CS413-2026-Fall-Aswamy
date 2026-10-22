"""Output and evaluation semantics of the print primitive."""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lambda2 as L


class PrintTests(unittest.TestCase):
    def run_print(self, source):
        output = io.StringIO()
        with redirect_stdout(output):
            value = L.d0exp_evaluate(L.d0exp_parse(source))
        return value, output.getvalue()

    def test_value_formats(self):
        for source, expected in [
            ('42', '42'), ('-3', '-3'), ('true', 'true'), ('false', 'false'),
            ('()', '()'), ('(1,)', '(1,)'), ('(1, false)', '(1, false)'),
            ('list_nil()', '[]'),
            ('list_cons(1, list_cons(true, list_nil()))', '[1, true]'),
            ('optn_nil()', 'optn_nil()'),
            ('optn_cons((1, list_nil()))', 'optn_cons((1, []))'),
            ('lam (x) => x', '<lam>'), ('fix f(x) => f(x)', '<fix>'),
        ]:
            with self.subTest(source=source):
                self.assertEqual(self.run_print('print(' + source + ')'),
                                 (L.D0Vtupl(()), expected + '\n'))

    def test_evaluates_once_and_in_order(self):
        self.assertEqual(self.run_print('print(print(1))'),
                         (L.D0Vtupl(()), '1\n()\n'))
        self.assertEqual(self.run_print('let a = print(1) b = print(2) in 3 end'),
                         (L.D0Vint(3), '1\n2\n'))
        self.assertEqual(self.run_print('if false then print(1) else ()'),
                         (L.D0Vtupl(()), ''))

    def test_failed_operand_does_not_print(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(ZeroDivisionError):
            L.d0exp_evaluate(L.d0exp_parse('print(1/0)'))
        self.assertEqual(output.getvalue(), '')

    def test_parser_and_free_variables(self):
        expr = L.d0exp_parse('print(x)')
        self.assertEqual(expr, L.D0Eop1('print', L.D0Evar('x')))
        self.assertEqual(L.d0exp_fvset(expr), frozenset({'x'}))
        for source in ('print()', 'print(1, 2)'):
            with self.assertRaises(L.LambdaSyntaxError):
                L.d0exp_parse(source)


if __name__ == '__main__':
    unittest.main()
