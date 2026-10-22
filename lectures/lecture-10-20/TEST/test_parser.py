"""Concrete syntax and end-to-end interpreter tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lambda2 as L
from basics0 import fnlist_cons, fnlist_nil


class ParserTests(unittest.TestCase):
    def test_list_nilq(self):
        self.assertEqual(L.d0exp_parse('list_nilq(xs)'),
                         L.D0Eop1('list_nilq', L.D0Evar('xs')))
        self.assertEqual(self.evaluate('list_nilq(list_nil())'), L.D0Vbtf(True))
        self.assertEqual(self.evaluate('list_nilq(list_cons(1, list_nil()))'),
                         L.D0Vbtf(False))
        self.assertEqual(self.evaluate('if list_nilq(list_nil()) then 1 else 2'),
                         L.D0Vint(1))
        for source in ('list_nilq()', 'list_nilq(xs, ys)'):
            with self.subTest(source=source), self.assertRaises(L.LambdaSyntaxError):
                L.d0exp_parse(source)

    def test_list_cons(self):
        self.assertEqual(L.d0exp_parse('list_cons(x, xs)'),
                         L.D0Eop2('list_cons', L.D0Evar('x'), L.D0Evar('xs')))
        self.assertEqual(self.evaluate('list_cons(1+2, list_cons(true, list_nil()))'),
                         L.D0Vlist(fnlist_cons(L.D0Vint(3),
                                   fnlist_cons(L.D0Vbtf(True), fnlist_nil()))))
        for source in ('list_cons()', 'list_cons(1)', 'list_cons(1,)',
                       'list_cons(1, list_nil(), 2)'):
            with self.subTest(source=source), self.assertRaises(L.LambdaSyntaxError):
                L.d0exp_parse(source)

    def test_list_nil(self):
        self.assertEqual(L.d0exp_parse('list_nil()'), L.D0Eop0('list_nil'))
        self.assertEqual(self.evaluate('let xs = list_nil() in xs end'),
                         L.D0Vlist(fnlist_nil()))
        for source in ('list_nil', 'list_nil(1)'):
            with self.subTest(source=source), self.assertRaises(L.LambdaSyntaxError):
                L.d0exp_parse(source)

    def evaluate(self, source):
        return L.d0exp_evaluate(L.d0exp_parse(source))

    def test_precedence_and_associativity(self):
        for source, expected in [
            ('2 + 3 * 4', 14), ('(2 + 3) * 4', 20),
            ('10 - 3 - 2', 5), ('24 / 3 / 2', 4),
            ('-7 / 3', -3), ('2 * -3 + +4', -2), ('--5', 5),
        ]:
            with self.subTest(source=source):
                self.assertEqual(self.evaluate(source), L.D0Vint(expected))
        self.assertEqual(self.evaluate('2 + 3 * 4 == 14'), L.D0Vbtf(True))

    def test_comparisons(self):
        for operator in ('<', '>', '<=', '>=', '==', '!='):
            with self.subTest(operator=operator):
                self.assertEqual(L.d0exp_parse('1 ' + operator + ' 2'),
                                 L.D0Eop2(operator, L.D0Eint(1), L.D0Eint(2)))

    def test_tuple_forms(self):
        for source, expected in [
            ('()', L.D0Etupl(())), ('(1)', L.D0Eint(1)),
            ('(1,)', L.D0Etupl((L.D0Eint(1),))),
            ('(1,true,)', L.D0Etupl((L.D0Eint(1), L.D0Ebtf(True)))),
        ]:
            with self.subTest(source=source):
                self.assertEqual(L.d0exp_parse(source), expected)
        self.assertEqual(self.evaluate('(1, (false, 9)).1.0'), L.D0Vbtf(False))

    def test_call_argument_shapes(self):
        for source, argument in [
            ('f()', L.D0Etupl(())), ('f(1)', L.D0Eint(1)),
            ('f(1,)', L.D0Etupl((L.D0Eint(1),))),
            ('f(1,2)', L.D0Etupl((L.D0Eint(1), L.D0Eint(2)))),
        ]:
            with self.subTest(source=source):
                self.assertEqual(L.d0exp_parse(source), L.D0Eapp(L.D0Evar('f'), argument))

    def test_chained_calls_and_projections(self):
        self.assertEqual(self.evaluate('(lam (x) => lam (y) => x+y)(2)(3)'),
                         L.D0Vint(5))
        self.assertEqual(self.evaluate('((lam (x) => x+1),).0(4)'), L.D0Vint(5))
        self.assertEqual(self.evaluate('(lam (x) => (x,))(7).0'), L.D0Vint(7))

    def test_sequential_declarations(self):
        source = 'let x = 2; y = x + 3 x = y * 2; in x + y end'
        parsed = L.d0exp_parse(source)
        self.assertIsInstance(parsed, L.D0Elets)
        self.assertIsInstance(parsed.arg1, fnlist_cons)
        self.assertEqual(L.d0exp_evaluate(parsed), L.D0Vint(15))
        self.assertEqual(L.d0exp_fvset(parsed), frozenset())
        self.assertEqual(self.evaluate('let in 8 end'), L.D0Vint(8))

    def test_top_level_declarations(self):
        declarations = L.d0cls_parse('x = 6\nanswer = x * 7;')
        self.assertEqual(L.d0exp_evaluate(L.D0Elets(declarations, L.D0Evar('answer'))),
                         L.D0Vint(42))
        self.assertIsInstance(L.d0cls_parse('# empty\n'), fnlist_nil)

    def test_lexical_scope(self):
        source = 'let x = 10 f = lam (y) => x+y x = 100 in f(2) end'
        self.assertEqual(self.evaluate(source), L.D0Vint(12))

    def test_conditionals(self):
        self.assertEqual(self.evaluate('if true then if false then 1 else 2 else 3'),
                         L.D0Vint(2))
        self.assertEqual(self.evaluate('if false then 1/0 else 9'), L.D0Vint(9))

    def test_comments_and_identifiers(self):
        self.assertEqual(self.evaluate('let # comment\n _x2 = 7 in _x2 end # done'),
                         L.D0Vint(7))
        self.assertEqual(L.d0exp_parse('true_value'), L.D0Evar('true_value'))

    def test_documented_factorials(self):
        source = (Path(__file__).resolve().parents[1] / 'SYNTAX.md').read_text()
        examples = source.split('```text\n')[2:]
        self.assertEqual(len(examples), 2)
        for example in examples:
            with self.subTest(example=example[:50]):
                self.assertEqual(self.evaluate(example.split('```')[0]), L.D0Vint(120))

    def test_readme_examples_parse(self):
        source = (Path(__file__).resolve().parents[1] / 'README.00').read_text()
        examples = source[source.index('fact ='):]
        declarations = L.d0cls_parse(examples)
        self.assertIsInstance(declarations.arg1.arg2, L.D0Efix)
        self.assertIsInstance(declarations.arg2.arg1.arg2, L.D0Elam)
        self.assertIsInstance(declarations.arg2.arg2, fnlist_nil)

    def test_parser_does_not_evaluate(self):
        self.assertIsInstance(L.d0exp_parse('1/0'), L.D0Eop2)
        self.assertEqual(L.d0exp_fvset(L.d0exp_parse('let x = y in x+z end')),
                         frozenset({'y', 'z'}))

    def test_invalid_expressions(self):
        for source in ('', '1 2', 'f x', '1 +', '(1', '(,)', '(1,,2)',
                       'f(1 2)', 'x.-1', 'x.y', '1 < 2 < 3', '@',
                       'lam () => 1', 'lam (x,y) => x', 'fix f(x) x',
                       'if true then 1', 'let x = in x end',
                       'let x = 1 in x', 'let true = 1 in true end',
                       'let x = 1;; in x end', '1;'):
            with self.subTest(source=source), self.assertRaises(L.LambdaSyntaxError):
                L.d0exp_parse(source)

    def test_invalid_declarations(self):
        for source in ('1', 'x', 'x =', 'x = 1; garbage', 'x = 1 @'):
            with self.subTest(source=source), self.assertRaises(L.LambdaSyntaxError):
                L.d0cls_parse(source)

    def test_error_locations(self):
        for source, line, column in [('let x = 1 in\n  @ end', 2, 3),
                                     ('1 +\n', 2, 1), ('(1\n  2)', 2, 3)]:
            with self.subTest(source=source):
                with self.assertRaises(L.LambdaSyntaxError) as caught:
                    L.d0exp_parse(source)
                self.assertEqual(caught.exception.lineno, line)
                self.assertEqual(caught.exception.offset, column)


if __name__ == '__main__':
    unittest.main()
