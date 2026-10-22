"""Option primitives and the declarations in mylib/optn.lam."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import lambda2 as L
from basics0 import fnoptn_nil, fnoptn_cons, fnlist_nil, fnlist_cons


class OptionLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.declarations = L.d0cls_parse(
            (Path(__file__).resolve().parents[1] / 'optn.lam').read_text())

    def evaluate(self, source):
        return L.d0exp_evaluate(L.D0Elets(self.declarations, L.d0exp_parse(source)))

    def test_primitives(self):
        self.assertEqual(self.evaluate('optn_nil()'), L.D0Voptn(fnoptn_nil()))
        self.assertEqual(self.evaluate('optn_cons(3)'), L.D0Voptn(fnoptn_cons(L.D0Vint(3))))
        self.assertEqual(self.evaluate('optn_nilq(optn_nil())'), L.D0Vbtf(True))
        self.assertEqual(self.evaluate('optn_nilq(optn_cons(false))'), L.D0Vbtf(False))
        self.assertEqual(self.evaluate('optn_get(optn_cons(false))'), L.D0Vbtf(False))
        self.assertEqual(self.evaluate('optn_get(optn_cons(optn_nil()))'), L.D0Voptn(fnoptn_nil()))
        with self.assertRaises(ValueError):
            self.evaluate('optn_get(optn_nil())')
        for name in ('optn_get', 'optn_nilq'):
            with self.assertRaises(TypeError):
                self.evaluate(name + '(1)')
        with self.assertRaises(ZeroDivisionError):
            self.evaluate('optn_cons(1/0)')

    def test_parser_and_free_variables(self):
        self.assertEqual(L.d0exp_parse('optn_nil()'), L.D0Eop0('optn_nil'))
        for name in ('optn_cons', 'optn_nilq', 'optn_get'):
            expr = L.d0exp_parse(name + '(x)')
            self.assertEqual(expr, L.D0Eop1(name, L.D0Evar('x')))
            self.assertEqual(L.d0exp_fvset(expr), frozenset({'x'}))
            for args in ('()', '(1,2)'):
                with self.assertRaises(L.LambdaSyntaxError):
                    L.d0exp_parse(name + args)
        with self.assertRaises(L.LambdaSyntaxError):
            L.d0exp_parse('optn_nil(1)')
        self.assertEqual(L.d0exp_fvset(L.D0Elets(self.declarations, L.D0Eint(0))), frozenset())

    def test_queries_and_defaults(self):
        for opt, present in [('optn_nil()', False), ('optn_cons(7)', True)]:
            self.assertEqual(self.evaluate(f'optn_someq({opt})'), L.D0Vbtf(present))
            self.assertEqual(self.evaluate(f'optn_length({opt})'), L.D0Vint(int(present)))
            self.assertEqual(self.evaluate(f'optn_get_default({opt}, 9)'), L.D0Vint(7 if present else 9))
        self.assertEqual(self.evaluate('optn_get_else(optn_nil(), lam (u) => 9)'), L.D0Vint(9))
        self.assertEqual(self.evaluate('optn_get_else(optn_cons(7), lam (u) => 1/0)'), L.D0Vint(7))
        with self.assertRaises(ZeroDivisionError):
            self.evaluate('optn_get_default(optn_cons(7), 1/0)')

    def test_map_bind_filter(self):
        some = L.D0Voptn(fnoptn_cons(L.D0Vint(8)))
        none = L.D0Voptn(fnoptn_nil())
        self.assertEqual(self.evaluate('optn_map(optn_cons(4), lam (x) => x*2)'), some)
        self.assertEqual(self.evaluate('optn_bind(optn_cons(4), lam (x) => optn_cons(x*2))'), some)
        self.assertEqual(self.evaluate('optn_bind(optn_cons(4), lam (x) => optn_nil())'), none)
        self.assertEqual(self.evaluate('optn_filter(optn_cons(8), lam (x) => x>5)'), some)
        self.assertEqual(self.evaluate('optn_filter(optn_cons(8), lam (x) => x<5)'), none)
        for name in ('optn_map', 'optn_bind', 'optn_filter'):
            self.assertEqual(self.evaluate(name + '(optn_nil(), lam (x) => 1/0)'), none)

    def test_fold_and_predicates(self):
        self.assertEqual(self.evaluate('optn_fold(optn_nil(), 9, lam (x) => 1/0)'), L.D0Vint(9))
        self.assertEqual(self.evaluate('optn_fold(optn_cons(4), 9, lam (x) => x*2)'), L.D0Vint(8))
        for name, empty in [('optn_exists', False), ('optn_forall', True)]:
            self.assertEqual(self.evaluate(name + '(optn_nil(), lam (x) => 1/0)'), L.D0Vbtf(empty))
            for predicate, expected in [('x>3', True), ('x<3', False)]:
                self.assertEqual(self.evaluate(name + '(optn_cons(4), lam (x) => ' + predicate + ')'),
                                 L.D0Vbtf(expected))

    def test_fallback_and_list_conversion(self):
        some = L.D0Voptn(fnoptn_cons(L.D0Vint(7)))
        self.assertEqual(self.evaluate('optn_or_else(optn_nil(), lam (u) => optn_cons(7))'), some)
        self.assertEqual(self.evaluate('optn_or_else(optn_cons(7), lam (u) => 1/0)'), some)
        self.assertEqual(self.evaluate('optn_to_list(optn_nil())'), L.D0Vlist(fnlist_nil()))
        self.assertEqual(self.evaluate('optn_to_list(optn_cons(7))'),
                         L.D0Vlist(fnlist_cons(L.D0Vint(7), fnlist_nil())))


if __name__ == '__main__':
    unittest.main()
