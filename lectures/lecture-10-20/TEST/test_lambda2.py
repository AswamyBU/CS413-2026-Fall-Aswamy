"""Behavioral tests for lambda2.py; requires Python 3.12 or later."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lambda2 as L
from basics0 import fnlist_nil, fnlist_cons


def declarations(*items):
    result = fnlist_nil()
    for item in reversed(items):
        result = fnlist_cons(item, result)
    return result


class EvaluationTests(unittest.TestCase):
    def test_list_nilq(self):
        empty = L.D0Eop0('list_nil')
        nonempty = L.D0Eop2('list_cons', L.D0Eint(1), empty)
        for operand, expected in ((empty, True), (nonempty, False)):
            with self.subTest(expected=expected):
                self.assertEqual(L.d0exp_evaluate(L.D0Eop1('list_nilq', operand)),
                                 L.D0Vbtf(expected))
        self.assertEqual(L.d0exp_fvset(L.D0Eop1('list_nilq', L.D0Evar('xs'))),
                         frozenset({'xs'}))
        with self.assertRaises(TypeError):
            L.d0exp_evaluate(L.D0Eop1('list_nilq', L.D0Eint(0)))

    def test_list_cons(self):
        tail = fnlist_cons(L.D0Vbtf(True), fnlist_nil())
        env = L.ENVcns('xs', L.D0Vlist(tail), L.ENVnil())
        expr = L.D0Eop2('list_cons', L.D0Eint(7), L.D0Evar('xs'))
        result = L.d0exp_evaluate(expr, env)
        self.assertEqual(result, L.D0Vlist(fnlist_cons(L.D0Vint(7), tail)))
        self.assertIs(result.arg1.arg2, tail)
        self.assertEqual(L.d0exp_fvset(expr), frozenset({'xs'}))

    def test_list_cons_requires_list_tail(self):
        with self.assertRaises(TypeError):
            L.d0exp_evaluate(L.D0Eop2('list_cons', L.D0Eint(1), L.D0Eint(2)))

    def test_list_nil(self):
        expr = L.D0Eop0('list_nil')
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vlist(fnlist_nil()))
        self.assertEqual(L.d0exp_fvset(expr), frozenset())

    def test_unknown_nullary_operator(self):
        with self.assertRaises(TypeError):
            L.d0exp_evaluate(L.D0Eop0('unknown'))

    def test_integer_operators(self):
        for op, expected in [('+', 10), ('-', 4), ('*', 21), ('/', 2)]:
            with self.subTest(op=op):
                expr = L.D0Eop2(op, L.D0Eint(7), L.D0Eint(3))
                self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(expected))
        for op, expected in [('+1', 8), ('-1', 6)]:
            with self.subTest(op=op):
                self.assertEqual(
                    L.d0exp_evaluate(L.D0Eop1(op, L.D0Eint(7))),
                    L.D0Vint(expected))

    def test_comparisons(self):
        for op, expected in [('<', False), ('>', True), ('<=', False),
                             ('>=', True), ('==', False), ('!=', True)]:
            with self.subTest(op=op):
                self.assertEqual(L.d0exp_evaluate(
                    L.D0Eop2(op, L.D0Eint(7), L.D0Eint(3))),
                    L.D0Vbtf(expected))

    def test_conditional_only_evaluates_selected_branch(self):
        bad = L.D0Eop2('/', L.D0Eint(1), L.D0Eint(0))
        for expr in [L.D0Eif0(L.D0Ebtf(True), L.D0Eint(8), bad),
                     L.D0Eif0(L.D0Ebtf(False), bad, L.D0Eint(8))]:
            self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(8))

    def test_let_initializer_uses_outer_binding(self):
        expr = L.D0Elet('x', L.D0Eint(4), L.D0Elet(
            'x', L.D0Eop1('+1', L.D0Evar('x')), L.D0Evar('x')))
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(5))

    def test_sequential_declarations_and_shadowing(self):
        expr = L.D0Elets(declarations(
            L.D0Cval('x', L.D0Eint(4)),
            L.D0Cval('y', L.D0Eop1('+1', L.D0Evar('x'))),
            L.D0Cval('x', L.D0Eop2('*', L.D0Evar('x'), L.D0Evar('y'))),
        ), L.D0Etupl((L.D0Evar('x'), L.D0Evar('y'))))
        self.assertEqual(L.d0exp_evaluate(expr),
                         L.D0Vtupl((L.D0Vint(20), L.D0Vint(5))))

    def test_empty_declarations_preserve_environment(self):
        env = L.ENVcns('x', L.D0Vint(9), L.ENVnil())
        self.assertEqual(L.d0exp_evaluate(L.D0Elets(fnlist_nil(), L.D0Evar('x')), env),
                         L.D0Vint(9))

    def test_long_declaration_list(self):
        dcls = fnlist_nil()
        for i in reversed(range(1500)):
            dcls = fnlist_cons(L.D0Cval('x', L.D0Eint(i)), dcls)
        expr = L.D0Elets(dcls, L.D0Evar('x'))
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(1499))
        self.assertEqual(L.d0exp_fvset(expr), frozenset())

    def test_invalid_declaration_list(self):
        for dcls in ([], fnlist_cons(L.D0Cval('x', L.D0Eint(1)), None)):
            expr = L.D0Elets(dcls, L.D0Eint(0))
            with self.assertRaises(TypeError):
                L.d0exp_evaluate(expr)
            with self.assertRaises(TypeError):
                L.d0exp_fvset(expr)

    def test_closure_captures_lexical_environment(self):
        expr = L.D0Elets(declarations(
            L.D0Cval('x', L.D0Eint(10)),
            L.D0Cval('f', L.D0Elam('y', L.D0Eop2(
                '+', L.D0Evar('x'), L.D0Evar('y')))),
            L.D0Cval('x', L.D0Eint(100)),
        ), L.D0Eapp(L.D0Evar('f'), L.D0Eint(2)))
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(12))

    def test_recursive_factorial(self):
        n = L.D0Evar('n')
        fact = L.D0Efix('fact', 'n', L.D0Eif0(
            L.D0Eop2('<=', n, L.D0Eint(1)), L.D0Eint(1),
            L.D0Eop2('*', n, L.D0Eapp(
                L.D0Evar('fact'), L.D0Eop1('-1', n)))))
        self.assertEqual(L.d0exp_evaluate(L.D0Eapp(fact, L.D0Eint(5))),
                         L.D0Vint(120))

    def test_application_evaluates_unused_argument(self):
        expr = L.D0Eapp(L.D0Elam('x', L.D0Eint(0)),
                       L.D0Eop2('/', L.D0Eint(1), L.D0Eint(0)))
        with self.assertRaises(ZeroDivisionError):
            L.d0exp_evaluate(expr)

    def test_tuple_lengths_and_projection(self):
        for size in (0, 1, 2, 5):
            with self.subTest(size=size):
                expr = L.D0Etupl(tuple(L.D0Eint(i) for i in range(size)))
                self.assertEqual(L.d0exp_evaluate(expr),
                                 L.D0Vtupl(tuple(L.D0Vint(i) for i in range(size))))
                for index in range(size):
                    self.assertEqual(L.d0exp_evaluate(L.D0Eproj(expr, index)),
                                     L.D0Vint(index))

    def test_nested_mixed_tuple(self):
        expr = L.D0Etupl((L.D0Ebtf(True), L.D0Etupl((L.D0Eint(8),))))
        self.assertEqual(L.d0exp_evaluate(L.D0Eproj(expr, 0)), L.D0Vbtf(True))
        self.assertEqual(L.d0exp_evaluate(L.D0Eproj(L.D0Eproj(expr, 1), 0)),
                         L.D0Vint(8))

    def test_projection_evaluates_all_tuple_components(self):
        expr = L.D0Eproj(L.D0Etupl((L.D0Eint(8),
            L.D0Eop2('/', L.D0Eint(1), L.D0Eint(0)))), 0)
        with self.assertRaises(ZeroDivisionError):
            L.d0exp_evaluate(expr)

    def test_invalid_projection_indices(self):
        for size, index in [(0, 0), (2, -1), (2, 2)]:
            with self.subTest(size=size, index=index):
                expr = L.D0Etupl(tuple(L.D0Eint(i) for i in range(size)))
                with self.assertRaises(IndexError):
                    L.d0exp_evaluate(L.D0Eproj(expr, index))

    def test_type_errors(self):
        expressions = [
            L.D0Eproj(L.D0Eint(1), 0),
            L.D0Eif0(L.D0Eint(1), L.D0Eint(2), L.D0Eint(3)),
            L.D0Eop1('+1', L.D0Ebtf(True)),
            L.D0Eop2('+', L.D0Eint(1), L.D0Ebtf(True)),
            L.D0Eapp(L.D0Eint(1), L.D0Eint(2)),
            L.D0Elets(declarations(L.D0C000()), L.D0Eint(0)),
        ]
        for expr in expressions:
            with self.subTest(expr=expr), self.assertRaises(TypeError):
                L.d0exp_evaluate(expr)


class FreeVariableTests(unittest.TestCase):
    def test_lambda_and_fix_binders(self):
        body = L.D0Eapp(L.D0Evar('f'), L.D0Eop2(
            '+', L.D0Evar('x'), L.D0Evar('y')))
        self.assertEqual(L.d0exp_fvset(L.D0Elam('x', body)), frozenset({'f', 'y'}))
        self.assertEqual(L.d0exp_fvset(L.D0Efix('f', 'x', body)), frozenset({'y'}))

    def test_let_initializer_is_outside_binding(self):
        expr = L.D0Elet('x', L.D0Evar('x'), L.D0Evar('x'))
        self.assertEqual(L.d0exp_fvset(expr), frozenset({'x'}))

    def test_sequential_scope_and_forward_reference(self):
        expr = L.D0Elets(declarations(
            L.D0Cval('x', L.D0Evar('y')),
            L.D0Cval('y', L.D0Evar('x')),
            L.D0Cval('x', L.D0Eop1('+1', L.D0Evar('x'))),
        ), L.D0Etupl((L.D0Evar('x'), L.D0Evar('y'), L.D0Evar('z'))))
        self.assertEqual(L.d0exp_fvset(expr), frozenset({'y', 'z'}))

    def test_empty_declarations(self):
        self.assertEqual(L.d0exp_fvset(L.D0Elets(fnlist_nil(), L.D0Evar('x'))),
                         frozenset({'x'}))

    def test_tuples_and_projection(self):
        self.assertEqual(L.d0exp_fvset(L.D0Etupl(())), frozenset())
        expr = L.D0Eproj(L.D0Etupl((L.D0Evar('x'), L.D0Evar('y'))), 0)
        self.assertEqual(L.d0exp_fvset(expr), frozenset({'x', 'y'}))

    def test_conditional_includes_both_branches_without_evaluation(self):
        expr = L.D0Eif0(L.D0Ebtf(True), L.D0Evar('x'),
                       L.D0Eop2('/', L.D0Evar('y'), L.D0Eint(0)))
        self.assertEqual(L.d0exp_fvset(expr), frozenset({'x', 'y'}))

    def test_unsupported_declaration(self):
        with self.assertRaises(TypeError):
            L.d0exp_fvset(L.D0Elets(declarations(L.D0C000()), L.D0Eint(0)))


if __name__ == '__main__':
    unittest.main()
