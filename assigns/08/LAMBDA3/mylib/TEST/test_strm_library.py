"""Lazy stream primitives and declarations in mylib/strm.lam."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import lambda3 as L


class StreamLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.declarations = L.d0cls_parse(
            (Path(__file__).resolve().parents[1] / 'strm.lam').read_text())
        L.d0cls_typecheck(cls.declarations)

    def evaluate(self, source):
        expr = L.D0Elets(self.declarations, L.d0exp_parse(source))
        return L.d0exp_evaluate(expr)

    def formatted(self, source):
        return L.d0val_format(self.evaluate(source))

    def test_construction_and_conversions(self):
        self.assertEqual(self.formatted('strm_nilq(strm_nil())'), 'true')
        self.assertEqual(self.formatted('strm_head(strm_singleton(8))'), '8')
        self.assertEqual(self.formatted('strm_to_list(strm_range(2, 6))'),
                         '[2, 3, 4, 5]')
        self.assertEqual(self.formatted(
            'strm_to_list(strm_make_list(list_cons(4, list_cons(7, list_nil()))))'),
            '[4, 7]')

    def test_lazy_transformations_and_slicing(self):
        self.assertEqual(self.formatted(
            'strm_to_list(strm_map(strm_range(1, 5), lam (x) => x*2))'),
            '[2, 4, 6, 8]')
        self.assertEqual(self.formatted(
            'strm_to_list(strm_filter(strm_range(0, 8), lam (x) => x>5))'),
            '[6, 7]')
        self.assertEqual(self.formatted(
            'strm_to_list(strm_take(strm_range(1, 10), 3))'), '[1, 2, 3]')
        self.assertEqual(self.formatted(
            'strm_to_list(strm_drop(strm_range(1, 6), 2))'), '[3, 4, 5]')
        self.assertEqual(self.formatted(
            'strm_to_list(strm_append(strm_range(1, 3), strm_range(3, 5)))'),
            '[1, 2, 3, 4]')

    def test_folds_and_predicates(self):
        self.assertEqual(self.formatted(
            'strm_foldleft(strm_range(1, 5), 0, lam (p) => p.0+p.1)'), '10')
        self.assertEqual(self.formatted(
            'strm_foldright(strm_range(1, 4), 0, lam (p) => p.0-p.1)'), '2')
        self.assertEqual(self.formatted(
            'strm_exists(strm_range(1, 8), lam (x) => x==4)'), 'true')
        self.assertEqual(self.formatted(
            'strm_forall(strm_range(1, 5), lam (x) => x<5)'), 'true')

    def test_operations_leave_unneeded_tails_unforced(self):
        self.assertEqual(self.formatted(
            'strm_head(strm_map(strm_cons(1, lazy_make(lam (u) => 1/0)), '
            'lam (x) => x+1))'), '2')
        self.assertEqual(self.formatted(
            'strm_exists(strm_cons(1, lazy_make(lam (u) => 1/0)), '
            'lam (x) => x==1)'), 'true')


if __name__ == '__main__':
    unittest.main()
