"""Tests for lambda1's closure-based call-by-value interpreter (Python 3.12+).

Run: python3 -B TEST/test03_lambda1.py
Also run with -O or -OO to verify that type checks survive optimization.
"""
import operator
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lambda1 import (
    D0E000, D0Eint, D0Ebtf, D0Evar, D0Elam, D0Efix, D0Eapp,
    D0Eif0, D0Elet, D0Eop1, D0Eop2, D0V000, D0Vint, D0Vbtf, D0Vlam,
    D0Epair, D0Epfst, D0Epsnd, D0Vpair,
    D0Vfix, ENVnil, ENVcns, d0env_search, d0exp_evaluate,
)


def let(name, value, body):
    """Construct let name = value in body."""
    return D0Elet(name, value, body)


def divide_by_zero():
    return D0Eop2('/', D0Eint(1), D0Eint(0))


class TestLambda1(unittest.TestCase):
    def test_literals(self):
        for term, expected in [(D0Eint(-42), D0Vint(-42)),
                               (D0Ebtf(True), D0Vbtf(True)),
                               (D0Ebtf(False), D0Vbtf(False))]:
            with self.subTest(term=term):
                self.assertEqual(d0exp_evaluate(term), expected)

    def test_unary_arithmetic(self):
        for n in (-3, 0, 4):
            for op, expected in [('+1', n + 1), ('-1', n - 1)]:
                with self.subTest(op=op, n=n):
                    self.assertEqual(d0exp_evaluate(D0Eop1(op, D0Eint(n))),
                                     D0Vint(expected))

    def test_binary_arithmetic(self):
        cases = [('+', 7, 3, 10), ('-', 3, 7, -4), ('*', -7, 3, -21),
                 ('/', 7, 3, 2), ('/', -7, 3, -3), ('/', 7, -3, -3)]
        for op, a, b, expected in cases:
            with self.subTest(op=op, a=a, b=b):
                self.assertEqual(d0exp_evaluate(D0Eop2(op, D0Eint(a), D0Eint(b))),
                                 D0Vint(expected))

    def test_comparisons(self):
        for a, b in [(2, 3), (3, 3), (4, 3)]:
            for op, compare in [('<', operator.lt), ('>', operator.gt),
                                ('<=', operator.le), ('>=', operator.ge),
                                ('==', operator.eq), ('!=', operator.ne)]:
                with self.subTest(op=op, a=a, b=b):
                    self.assertEqual(
                        d0exp_evaluate(D0Eop2(op, D0Eint(a), D0Eint(b))),
                        D0Vbtf(compare(a, b)))

    def test_integer_operands_required(self):
        # unittest assertions remain active under python -O and -OO.
        for bad in [D0Ebtf(True), D0Elam('x', D0Evar('x'))]:
            for op in ('+1', '-1'):
                with self.subTest(op=op, bad=bad):
                    with self.assertRaises(TypeError):
                        d0exp_evaluate(D0Eop1(op, bad))
            for op in ('+', '-', '*', '/', '<', '>', '<=', '>=', '==', '!='):
                for a, b in [(bad, D0Eint(2)), (D0Eint(2), bad)]:
                    with self.subTest(op=op, a=a, b=b):
                        with self.assertRaises(TypeError):
                            d0exp_evaluate(D0Eop2(op, a, b))

    def test_conditional_requires_boolean(self):
        for bad in [D0Eint(0), D0Eint(1), D0Elam('x', D0Evar('x'))]:
            with self.subTest(condition=bad):
                with self.assertRaises(TypeError):
                    d0exp_evaluate(D0Eif0(bad, D0Eint(1), D0Eint(2)))

    def test_conditional_only_evaluates_selected_branch(self):
        for flag in (True, False):
            condition = D0Eapp(D0Elam('x', D0Evar('x')), D0Ebtf(flag))
            good, bad = D0Eint(7), divide_by_zero()
            term = D0Eif0(condition, good if flag else bad, bad if flag else good)
            with self.subTest(flag=flag):
                self.assertEqual(d0exp_evaluate(term), D0Vint(7))

    def test_unsupported_terms_and_operators(self):
        for term in [D0E000(), D0Eop1('unknown', D0Eint(1)),
                     D0Eop2('unknown', D0Eint(1), D0Eint(2))]:
            with self.subTest(term=term):
                with self.assertRaises(TypeError):
                    d0exp_evaluate(term)

    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            d0exp_evaluate(divide_by_zero())

    def test_environment_lookup_and_shadowing(self):
        outer = ENVcns('x', D0Vint(1), ENVnil())
        inner = ENVcns('x', D0Vint(2), outer)
        self.assertEqual(d0env_search(inner, 'x'), D0Vint(2))
        self.assertEqual(d0env_search(outer, 'x'), D0Vint(1))
        self.assertEqual(d0exp_evaluate(D0Evar('x'), inner), D0Vint(2))
        # The interpreter deliberately uses D0V000 as its missing-name sentinel.
        self.assertEqual(d0exp_evaluate(D0Evar('missing')), D0V000())

    def test_closures_capture_environment_without_evaluating_body(self):
        env = ENVcns('x', D0Vint(10), ENVnil())
        for code, kind in [(D0Elam('y', divide_by_zero()), D0Vlam),
                           (D0Efix('f', 'y', divide_by_zero()), D0Vfix)]:
            with self.subTest(code=code):
                value = d0exp_evaluate(code, env)
                self.assertIsInstance(value, kind)
                self.assertIs(value.arg1, env)
                self.assertIs(value.arg2, code)

    def test_lexical_scope(self):
        # let x=10; let f=(lambda y. x+y); let x=100; f(2)
        term = let('x', D0Eint(10), let('f',
            D0Elam('y', D0Eop2('+', D0Evar('x'), D0Evar('y'))),
            let('x', D0Eint(100), D0Eapp(D0Evar('f'), D0Eint(2)))))
        self.assertEqual(d0exp_evaluate(term), D0Vint(12))

    def test_let_initializer_uses_outer_binding_and_scope_is_local(self):
        env = ENVcns('x', D0Vint(10), ENVnil())
        term = D0Epair(
            let('x', D0Eop1('+1', D0Evar('x')), D0Evar('x')),
            D0Evar('x'))
        self.assertEqual(d0exp_evaluate(term, env),
                         D0Vpair(D0Vint(11), D0Vint(10)))

    def test_unused_let_initializer_evaluated_before_body(self):
        term = let('x', divide_by_zero(), D0Eop1('+1', D0Ebtf(True)))
        with self.assertRaises(ZeroDivisionError):
            d0exp_evaluate(term)

    def test_independent_closures(self):
        make = D0Elam('x', D0Elam('y', D0Evar('x')))
        term = let('make', make, let('a', D0Eapp(D0Evar('make'), D0Eint(10)),
            let('b', D0Eapp(D0Evar('make'), D0Eint(20)),
                D0Eop2('+', D0Eapp(D0Evar('a'), D0Eint(0)),
                            D0Eapp(D0Evar('b'), D0Eint(0))))))
        self.assertEqual(d0exp_evaluate(term), D0Vint(30))

    def test_parameter_shadowing(self):
        term = D0Eapp(D0Eapp(D0Elam('x', D0Elam('x', D0Evar('x'))),
                             D0Eint(1)), D0Eint(2))
        self.assertEqual(d0exp_evaluate(term), D0Vint(2))
        term = D0Eapp(D0Efix('x', 'x', D0Evar('x')), D0Eint(7))
        self.assertEqual(d0exp_evaluate(term), D0Vint(7))

    def test_free_variable_not_resolved_at_call_site(self):
        term = let('f', D0Elam('y', D0Evar('x')),
                   let('x', D0Eint(10), D0Eapp(D0Evar('f'), D0Eint(0))))
        self.assertEqual(d0exp_evaluate(term), D0V000())

    def test_recursive_factorial(self):
        factorial = D0Efix('f', 'n', D0Eif0(
            D0Eop2('<=', D0Evar('n'), D0Eint(1)), D0Eint(1),
            D0Eop2('*', D0Evar('n'),
                D0Eapp(D0Evar('f'), D0Eop1('-1', D0Evar('n'))))))
        for n, expected in [(0, 1), (1, 1), (5, 120), (7, 5040)]:
            with self.subTest(n=n):
                self.assertEqual(d0exp_evaluate(D0Eapp(factorial, D0Eint(n))),
                                 D0Vint(expected))

    def test_tail_recursive_factorial(self):
        # loop(n, acc) = acc if n <= 1 else loop(n - 1, n * acc).
        # Pass both arguments as a pair; use let to name its components.
        loop = D0Efix('loop', 'state',
            D0Elet('n', D0Epfst(D0Evar('state')),
                D0Elet('acc', D0Epsnd(D0Evar('state')),
                    D0Eif0(
                        D0Eop2('<=', D0Evar('n'), D0Eint(1)),
                        D0Evar('acc'),
                        D0Eapp(D0Evar('loop'), D0Epair(
                            D0Eop1('-1', D0Evar('n')),
                            D0Eop2('*', D0Evar('n'), D0Evar('acc'))))))))
        factorial = D0Elam('n', D0Elet('loop', loop,
            D0Eapp(D0Evar('loop'), D0Epair(D0Evar('n'), D0Eint(1)))))
        for n, expected in [(0, 1), (1, 1), (5, 120), (7, 5040), (10, 3628800)]:
            with self.subTest(n=n):
                self.assertEqual(d0exp_evaluate(D0Eapp(factorial, D0Eint(n))),
                                 D0Vint(expected))

    def test_recursive_closure_captures_outer_binding(self):
        function = D0Efix('f', 'n', D0Eif0(
            D0Eop2('<=', D0Evar('n'), D0Eint(0)), D0Eint(0),
            D0Eop2('+', D0Evar('step'),
                D0Eapp(D0Evar('f'), D0Eop1('-1', D0Evar('n'))))))
        term = let('step', D0Eint(3), let('g', function,
            let('step', D0Eint(100), let('f', D0Eint(999),
                D0Eapp(D0Evar('g'), D0Eint(4))))))
        self.assertEqual(d0exp_evaluate(term), D0Vint(12))

    def test_unused_argument_is_evaluated(self):
        for function in [D0Elam('x', D0Eint(42)), D0Efix('f', 'x', D0Eint(42))]:
            with self.subTest(function=function):
                with self.assertRaises(ZeroDivisionError):
                    d0exp_evaluate(D0Eapp(function, divide_by_zero()))

    def test_function_and_left_operand_evaluated_first(self):
        type_error = D0Eop1('+1', D0Ebtf(True))
        for term in [D0Eapp(divide_by_zero(), type_error),
                     D0Eop2('+', divide_by_zero(), type_error)]:
            with self.subTest(term=term):
                with self.assertRaises(ZeroDivisionError):
                    d0exp_evaluate(term)

    def test_application_requires_closure(self):
        for term in [D0Eint(1), D0Ebtf(True)]:
            with self.subTest(function=term):
                with self.assertRaises(TypeError):
                    d0exp_evaluate(D0Eapp(term, D0Eint(2)))


class TestLambda1Pairs(unittest.TestCase):
    def test_pair_components_evaluate_in_current_environment(self):
        term = let('x', D0Eint(4), D0Epair(
            D0Eop1('+1', D0Evar('x')),
            D0Eop2('==', D0Evar('x'), D0Eint(4))))
        self.assertEqual(d0exp_evaluate(term), D0Vpair(D0Vint(5), D0Vbtf(True)))

    def test_projections_of_computed_pair(self):
        pair = D0Eapp(D0Elam('x', D0Epair(D0Evar('x'), D0Ebtf(False))),
                      D0Eint(7))
        for projection, expected in [(D0Epfst, D0Vint(7)), (D0Epsnd, D0Vbtf(False))]:
            with self.subTest(projection=projection):
                term = let('p', pair, projection(D0Evar('p')))
                self.assertEqual(d0exp_evaluate(term), expected)

    def test_nested_pairs(self):
        pair = D0Epair(D0Eint(1), D0Epair(D0Eint(2), D0Eint(3)))
        self.assertEqual(d0exp_evaluate(pair),
                         D0Vpair(D0Vint(1), D0Vpair(D0Vint(2), D0Vint(3))))
        self.assertEqual(d0exp_evaluate(D0Epfst(D0Epsnd(pair))), D0Vint(2))
        self.assertEqual(d0exp_evaluate(D0Epsnd(D0Epsnd(pair))), D0Vint(3))

    def test_projected_closures_preserve_lexical_scope(self):
        for function in [D0Elam('y', D0Eop2('+', D0Evar('x'), D0Evar('y'))),
                         D0Efix('f', 'y', D0Eif0(
                             D0Eop2('<=', D0Evar('y'), D0Eint(0)), D0Evar('x'),
                             D0Eapp(D0Evar('f'), D0Eop1('-1', D0Evar('y')))))]:
            for projection in (D0Epfst, D0Epsnd):
                with self.subTest(function=function, projection=projection):
                    term = let('x', D0Eint(10),
                        let('p', D0Epair(function, function),
                            let('x', D0Eint(100),
                                D0Eapp(projection(D0Evar('p')), D0Eint(2)))))
                    expected = 12 if isinstance(function, D0Elam) else 10
                    self.assertEqual(d0exp_evaluate(term), D0Vint(expected))

    def test_pair_evaluates_left_before_right(self):
        term = D0Epair(divide_by_zero(), D0Eop1('+1', D0Ebtf(True)))
        with self.assertRaises(ZeroDivisionError):
            d0exp_evaluate(term)

    def test_projection_evaluates_both_components(self):
        # Even the component discarded by a projection must be evaluated.
        for projection in (D0Epfst, D0Epsnd):
            for pair in [D0Epair(D0Eint(1), divide_by_zero()),
                         D0Epair(divide_by_zero(), D0Eint(2))]:
                with self.subTest(projection=projection, pair=pair):
                    with self.assertRaises(ZeroDivisionError):
                        d0exp_evaluate(projection(pair))

    def test_projection_requires_pair(self):
        for projection in (D0Epfst, D0Epsnd):
            for term in [D0Eint(1), D0Ebtf(True), D0Elam('x', D0Evar('x')),
                         D0Efix('f', 'x', D0Evar('x')), D0Evar('missing')]:
                with self.subTest(projection=projection, term=term):
                    with self.assertRaises(TypeError):
                        d0exp_evaluate(projection(term))

    def test_pair_is_not_integer_boolean_or_function(self):
        pair = D0Epair(D0Eint(1), D0Eint(2))
        for term in [D0Eop1('+1', pair), D0Eop2('+', pair, D0Eint(1)),
                     D0Eif0(pair, D0Eint(1), D0Eint(2)), D0Eapp(pair, D0Eint(0))]:
            with self.subTest(term=term):
                with self.assertRaises(TypeError):
                    d0exp_evaluate(term)


if __name__ == '__main__':
    unittest.main(verbosity=2)
