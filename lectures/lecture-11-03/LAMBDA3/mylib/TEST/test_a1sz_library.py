"""Sized-array primitives and declarations in mylib/a1sz.lam."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import lambda3 as L


class A1szLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.declarations = L.d0cls_parse(
            (Path(__file__).resolve().parents[1] / 'a1sz.lam').read_text())
        L.d0cls_typecheck(cls.declarations)

    def evaluate(self, source):
        expr = L.D0Elets(self.declarations, L.d0exp_parse(source))
        return L.d0exp_evaluate(expr)

    def formatted(self, source):
        return L.d0val_format(self.evaluate(source))

    def test_construction_and_indexing(self):
        self.assertEqual(self.formatted('a1sz_make_ncpy(3, 8)'), '[8, 8, 8]')
        self.assertEqual(self.formatted('a1sz_make_nfun(4, lam (i) => i*2)'),
                         '[0, 2, 4, 6]')
        self.assertEqual(self.formatted('a1sz_size(a1sz_make_ncpy(3, true))'), '3')
        self.assertEqual(self.formatted('a1sz_getat(a1sz_make_nfun(3, lam (i) => i+4), 2)'), '6')
        with self.assertRaises(IndexError):
            self.evaluate('a1sz_getat(a1sz_make_ncpy(2, 0), 2)')
        with self.assertRaises(ValueError):
            self.evaluate('a1sz_make_ncpy(-1, 0)')

    def test_update(self):
        self.assertEqual(
            self.formatted('let xs = a1sz_make_ncpy(3, 5); r = a1sz_setat(xs, 1, 9) in (r, xs) end'),
            '((), [5, 9, 5])')
        self.assertEqual(L.format_type(L.d0exp_typecheck(
            L.d0exp_parse('a1sz_setat(a1sz_make_ncpy(1, 5), 0, 9)'))), 'void')

    def test_list_conversion(self):
        self.assertEqual(self.formatted('a1sz_make_list(list_nil())'), '[]')
        self.assertEqual(
            self.formatted('a1sz_make_list(list_cons(2, list_cons(4, list_cons(6, list_nil()))))'),
            '[2, 4, 6]')

    def test_array_transformations(self):
        self.assertEqual(self.formatted('a1sz_reverse(a1sz_make_nfun(4, lam (i) => i+1))'),
                         '[4, 3, 2, 1]')
        self.assertEqual(self.formatted(
            'a1sz_append(a1sz_make_nfun(2, lam (i) => i), a1sz_make_nfun(2, lam (i) => i+2))'),
            '[0, 1, 2, 3]')
        self.assertEqual(self.formatted(
            'a1sz_concat(a1sz_make_nfun(3, lam (i) => a1sz_make_nfun(2, lam (j) => i*2+j)))'),
            '[0, 1, 2, 3, 4, 5]')
        self.assertEqual(self.formatted(
            'a1sz_map(a1sz_make_nfun(3, lam (i) => i+1), lam (x) => x*3)'),
            '[3, 6, 9]')

    def test_filter_folds_and_predicates(self):
        self.assertEqual(self.formatted(
            'a1sz_filter_list(a1sz_make_nfun(6, lam (i) => i), lam (x) => x<3)'),
            '[0, 1, 2]')
        self.assertEqual(self.formatted(
            'a1sz_filter_list(a1sz_make_ncpy(0, 1), lam (x) => 1/0)'), '[]')
        self.assertEqual(self.formatted(
            'a1sz_foldleft(a1sz_make_nfun(4, lam (i) => i+1), 0, lam (p) => p.0+p.1)'),
            '10')
        self.assertEqual(self.formatted(
            'a1sz_foldright(a1sz_make_nfun(3, lam (i) => i+1), 0, lam (p) => p.0-p.1)'),
            '2')
        self.assertEqual(self.formatted(
            'a1sz_exists(a1sz_make_nfun(4, lam (i) => i), lam (x) => x==0)'), 'true')
        self.assertEqual(self.formatted(
            'a1sz_forall(a1sz_make_nfun(4, lam (i) => i), lam (x) => x<4)'), 'true')
        self.assertEqual(self.formatted(
            'a1sz_exists(a1sz_make_ncpy(0, 1), lam (x) => 1/0)'), 'false')


if __name__ == '__main__':
    unittest.main()
