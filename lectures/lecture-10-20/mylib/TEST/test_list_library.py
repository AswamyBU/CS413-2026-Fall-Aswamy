"""Parse and evaluate the declarations in mylib/list.lam."""
import sys
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import lambda2 as L
from basics0 import fnlist_nil, fnlist_cons


class ListLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (Path(__file__).resolve().parents[1] / 'list.lam').read_text()
        cls.declarations = L.d0cls_parse(source)

    def evaluate(self, source):
        return L.d0exp_evaluate(L.D0Elets(self.declarations, L.d0exp_parse(source)))

    def integers(self, source):
        value = self.evaluate(source)
        self.assertIsInstance(value, L.D0Vlist)
        result = []
        items = value.arg1
        while isinstance(items, fnlist_cons):
            self.assertIsInstance(items.arg1, L.D0Vint)
            result.append(items.arg1.arg1)
            items = items.arg2
        self.assertIsInstance(items, fnlist_nil)
        return result

    def test_library_is_closed(self):
        self.assertEqual(L.d0exp_fvset(L.D0Elets(self.declarations, L.D0Eint(0))),
                         frozenset())

    def test_list_print(self):
        for source, expected in [
            ('list_print(list_nil())', '[]\n'),
            ('list_print(list_range(1, 4))', '[1, 2, 3]\n'),
            ('list_print(list_singleton(true))', '[true]\n'),
            ('list_print(list_singleton(list_range(1, 3)))', '[[1, 2]]\n'),
        ]:
            with self.subTest(source=source):
                output = io.StringIO()
                with redirect_stdout(output):
                    result = self.evaluate(source)
                self.assertEqual(result, L.D0Vtupl(()))
                self.assertEqual(output.getvalue(), expected)

    def test_construction_and_length(self):
        self.assertEqual(self.integers('list_singleton(9)'), [9])
        self.assertEqual(self.integers('list_range(2, 5)'), [2, 3, 4])
        self.assertEqual(self.integers('list_range(5, 2)'), [])
        self.assertEqual(self.evaluate('list_length(list_range(0, 5))'), L.D0Vint(5))
        self.assertEqual(self.evaluate('list_length(list_nil())'), L.D0Vint(0))

    def test_reverse_append_concat(self):
        cases = [
            ('list_reverse(list_range(1, 4))', [3, 2, 1]),
            ('list_reverse(list_nil())', []),
            ('list_append(list_range(1, 3), list_range(3, 5))', [1, 2, 3, 4]),
            ('list_append(list_nil(), list_singleton(7))', [7]),
            ('list_concat(list_cons(list_range(1,3), list_cons(list_nil(), '
             'list_cons(list_singleton(3), list_nil()))))', [1, 2, 3]),
            ('list_concat(list_nil())', []),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(self.integers(source), expected)

    def test_map_filter(self):
        self.assertEqual(self.integers('list_map(list_range(1,4), lam (x) => x*2)'),
                         [2, 4, 6])
        self.assertEqual(self.integers('list_filter(list_range(1,5), lam (x) => x>2)'),
                         [3, 4])
        for operation in ('list_map', 'list_filter'):
            self.assertEqual(self.integers(operation + '(list_nil(), lam (x) => 1/0)'), [])

    def test_fold_direction(self):
        self.assertEqual(self.evaluate(
            'list_foldleft(list_range(1,4), 0, lam (p) => p.0-p.1)'), L.D0Vint(-6))
        self.assertEqual(self.evaluate(
            'list_foldright(list_range(1,4), 0, lam (p) => p.0-p.1)'), L.D0Vint(2))
        for operation in ('list_foldleft', 'list_foldright'):
            self.assertEqual(self.evaluate(operation + '(list_nil(), 9, lam (p) => 1/0)'),
                             L.D0Vint(9))

    def test_predicates_short_circuit(self):
        for source, expected in [
            ('list_exists(list_nil(), lam (x) => 1/0)', False),
            ('list_forall(list_nil(), lam (x) => 1/0)', True),
            ('list_exists(list_range(0,3), lam (x) => if x==0 then true else 1/0)', True),
            ('list_forall(list_range(0,3), lam (x) => if x==0 then false else 1/0)', False),
            ('list_exists(list_range(0,3), lam (x) => x>5)', False),
            ('list_forall(list_range(0,3), lam (x) => x<5)', True),
        ]:
            with self.subTest(source=source):
                self.assertEqual(self.evaluate(source), L.D0Vbtf(expected))

    def test_take_drop_boundaries(self):
        for count in (-1, 0, 2, 3, 5):
            cut = max(0, count)
            with self.subTest(count=count):
                self.assertEqual(self.integers(f'list_take(list_range(0,3), {count})'),
                                 [0, 1, 2][:cut])
                self.assertEqual(self.integers(f'list_drop(list_range(0,3), {count})'),
                                 [0, 1, 2][cut:])
        self.assertEqual(self.integers('list_take(list_nil(), 2)'), [])
        self.assertEqual(self.integers('list_drop(list_nil(), 2)'), [])

    def test_head_tail_primitives(self):
        self.assertEqual(self.evaluate('list_head(list_singleton(true))'), L.D0Vbtf(True))
        self.assertEqual(self.integers('list_tail(list_range(1,4))'), [2, 3])
        for operator in ('list_head', 'list_tail'):
            self.assertEqual(L.d0exp_fvset(L.d0exp_parse(operator + '(xs)')),
                             frozenset({'xs'}))
            with self.assertRaises(ValueError):
                self.evaluate(operator + '(list_nil())')
            with self.assertRaises(TypeError):
                self.evaluate(operator + '(1)')
            for args in ('()', '(1, 2)'):
                with self.assertRaises(L.LambdaSyntaxError):
                    L.d0exp_parse(operator + args)


if __name__ == '__main__':
    unittest.main()
