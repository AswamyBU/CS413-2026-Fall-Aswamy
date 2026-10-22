"""Tests for the explicitly typed LAMBDA interpreter (Python 3.12+)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lambda2 as L


class TypeCheckingTests(unittest.TestCase):
    def checked(self, source):
        expr, typ = L.d0exp_parse_and_typecheck(source)
        return expr, typ

    def test_arithmetic_and_boolean_result_types(self):
        self.assertIsInstance(self.checked('6 * 7')[1], L.TInt)
        self.assertIsInstance(self.checked('6 < 7')[1], L.TBool)

    def test_annotated_lambda_and_application(self):
        expr, typ = self.checked('(lam (x : int) => x + 1)(41)')
        self.assertEqual(typ, L.TInt())
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(42))

    def test_conditionals_require_boolean_and_matching_branches(self):
        self.assertEqual(self.checked('if true then 1 else 2')[1], L.TInt())
        for source in ('if 1 then 2 else 3',
                       'if true then 1 else false'):
            with self.subTest(source=source), self.assertRaises(L.TypeCheckError):
                self.checked(source)

    def test_annotated_sequential_bindings(self):
        expr, typ = self.checked(
            'let x : int = 6 y : int = x * 7 in y end'
        )
        self.assertEqual(typ, L.TInt())
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(42))
        with self.assertRaises(L.TypeCheckError):
            self.checked('let x : bool = 6 in x end')

    def test_recursive_function_annotations(self):
        expr, typ = self.checked(
            'let fact : int -> int = '
            'fix fact(n: int): int => '
            'if n <= 1 then 1 else n * fact(n - 1) '
            'in fact(5) end'
        )
        self.assertEqual(typ, L.TInt())
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(120))
        with self.assertRaises(L.TypeCheckError):
            self.checked(
                'fix f(n: int): bool => n + 1'
            )

    def test_tuple_and_projection_types(self):
        expr, typ = self.checked(
            'let p : (int, bool) = (7, 7 < 10) in p.1 end'
        )
        self.assertEqual(typ, L.TBool())
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vbtf(True))
        with self.assertRaises(L.TypeCheckError):
            self.checked('(1, true).2')

    def test_lists_are_homogeneous_and_head_has_element_type(self):
        expr, typ = self.checked(
            'let xs : List[int] = list_cons(4, list_nil()) '
            'in list_head(xs) end'
        )
        self.assertEqual(typ, L.TInt())
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(4))
        with self.assertRaises(L.TypeCheckError):
            self.checked('list_cons(true, list_cons(1, list_nil()))')

    def test_options_are_parameterized(self):
        expr, typ = self.checked(
            'let value : Option[int] = optn_cons(9) '
            'in optn_get(value) end'
        )
        self.assertEqual(typ, L.TInt())
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(9))
        self.assertEqual(
            self.checked('let empty : Option[bool] = optn_nil() '
                         'in optn_nilq(empty) end')[1],
            L.TBool(),
        )

    def test_bad_operator_arguments_and_unbound_variables(self):
        for source in ('true + 1', '1(false)', 'missing + 1',
                       'list_head(1)', 'optn_get(list_nil())'):
            with self.subTest(source=source), self.assertRaises(L.TypeCheckError):
                self.checked(source)

    def test_declaration_sequence_checker(self):
        declarations = L.d0cls_parse('x : int = 2 y : int = x + 3')
        self.assertIsNone(L.d0cls_typecheck(declarations))
        bad = L.d0cls_parse('x : bool = 2')
        with self.assertRaises(L.TypeCheckError):
            L.d0cls_typecheck(bad)

    def test_type_formatting(self):
        self.assertEqual(
            L.format_type(L.TFun(L.TInt(), L.TFun(L.TBool(), L.TInt()))),
            'int -> bool -> int',
        )
        self.assertEqual(L.format_type(L.TTuple(())), 'unit')


if __name__ == '__main__':
    unittest.main()
