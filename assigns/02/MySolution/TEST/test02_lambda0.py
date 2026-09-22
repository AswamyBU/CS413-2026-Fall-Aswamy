"""Tests for pairs and projections (needs Python 3.12+)."""

import sys
import unittest
from pathlib import Path

# use MySolution/lambda0.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0,
    T0Mop1, T0Mop2, T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_size, t0erm_fvset, t0erm_subst0, t0erm_cbv_evaluate0,
)

ev = t0erm_cbv_evaluate0
DIV0 = T0Mop2("/", T0Mint(1), T0Mint(0))


class TestSize(unittest.TestCase):
    def test_pair(self):
        self.assertEqual(t0erm_size(T0Mpair(T0Mint(1), T0Mint(2))), 3)

    def test_projections(self):
        self.assertEqual(t0erm_size(T0Mpfst(T0Mint(1))), 2)
        self.assertEqual(t0erm_size(T0Mpsnd(T0Mint(1))), 2)

    def test_nested(self):
        pair = T0Mpair(T0Mint(1), T0Mint(2))                  # 3
        self.assertEqual(t0erm_size(T0Mpair(pair, pair)), 7)
        self.assertEqual(t0erm_size(T0Mpfst(T0Mpair(pair, T0Mvar("x")))), 1 + 1 + 3 + 1)
        self.assertEqual(t0erm_size(T0Mpsnd(T0Mpsnd(T0Mpfst(pair)))), 3 + 3)

    def test_inside_other_constructs(self):
        term = T0Mlam("x", T0Mif0(T0Mbtf(True),
                                  T0Mpair(T0Mvar("x"), T0Mint(0)),
                                  T0Mpfst(T0Mvar("x"))))
        self.assertEqual(t0erm_size(term), 1 + (1 + 1 + 3 + 2))
        term = T0Mfix("f", "x", T0Mapp(T0Mvar("f"), T0Mpsnd(T0Mvar("x"))))
        self.assertEqual(t0erm_size(term), 1 + (1 + 1 + 2))
        term = T0Mop2("+", T0Mpfst(T0Mvar("p")), T0Mpsnd(T0Mvar("p")))
        self.assertEqual(t0erm_size(term), 5)


class TestFreeVariables(unittest.TestCase):
    def test_pair_and_projections(self):
        self.assertEqual(t0erm_fvset(T0Mpair(T0Mint(1), T0Mint(2))), frozenset())
        self.assertEqual(t0erm_fvset(T0Mpair(T0Mvar("x"), T0Mvar("y"))),
                         frozenset({"x", "y"}))
        self.assertEqual(t0erm_fvset(T0Mpfst(T0Mvar("x"))), frozenset({"x"}))
        self.assertEqual(t0erm_fvset(T0Mpsnd(T0Mvar("y"))), frozenset({"y"}))

    def test_nested(self):
        term = T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))
        term = T0Mpair(T0Mpair(T0Mvar("a"), T0Mint(1)), T0Mpsnd(T0Mpair(T0Mvar("b"), T0Mvar("a"))))
        self.assertEqual(t0erm_fvset(term), frozenset({"a", "b"}))

    def test_binders_still_bind(self):
        pair = T0Mpair(T0Mvar("x"), T0Mvar("y"))
        self.assertEqual(t0erm_fvset(T0Mlam("x", pair)), frozenset({"y"}))
        self.assertEqual(t0erm_fvset(T0Mfix("f", "x", T0Mpair(T0Mvar("f"), pair))),
                         frozenset({"y"}))
        self.assertEqual(t0erm_fvset(T0Mlam("p", T0Mpfst(T0Mvar("p")))), frozenset())
        term = T0Mpair(T0Mlam("x", T0Mvar("x")), T0Mlam("y", T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset())

    def test_inside_other_constructs(self):
        term = T0Mapp(T0Mpfst(T0Mvar("f")), T0Mpair(T0Mvar("a"), T0Mvar("b")))
        self.assertEqual(t0erm_fvset(term), frozenset({"f", "a", "b"}))
        term = T0Mif0(T0Mbtf(True), T0Mpair(T0Mvar("a"), T0Mint(1)), T0Mpsnd(T0Mvar("b")))
        self.assertEqual(t0erm_fvset(term), frozenset({"a", "b"}))


class TestSubstitution(unittest.TestCase):
    def test_pair_components(self):
        term = T0Mpair(T0Mvar("x"), T0Mop2("+", T0Mvar("x"), T0Mvar("y")))
        expected = T0Mpair(T0Mint(7), T0Mop2("+", T0Mint(7), T0Mvar("y")))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)

    def test_projection_operands(self):
        self.assertEqual(t0erm_subst0(T0Mpfst(T0Mvar("x")), "x", T0Mint(7)),
                         T0Mpfst(T0Mint(7)))
        self.assertEqual(t0erm_subst0(T0Mpsnd(T0Mvar("x")), "x", T0Mint(7)),
                         T0Mpsnd(T0Mint(7)))
        self.assertIsInstance(t0erm_subst0(T0Mpfst(T0Mvar("x")), "x", T0Mint(7)), T0Mpfst)
        self.assertIsInstance(t0erm_subst0(T0Mpsnd(T0Mvar("x")), "x", T0Mint(7)), T0Mpsnd)

    def test_untouched_when_variable_absent(self):
        term = T0Mpair(T0Mvar("y"), T0Mpfst(T0Mvar("z")))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), term)

    def test_nested(self):
        term = T0Mpair(T0Mpair(T0Mvar("x"), T0Mint(1)), T0Mpsnd(T0Mpfst(T0Mvar("x"))))
        expected = T0Mpair(T0Mpair(T0Mstr("s"), T0Mint(1)), T0Mpsnd(T0Mpfst(T0Mstr("s"))))
        self.assertEqual(t0erm_subst0(term, "x", T0Mstr("s")), expected)

    def test_substitute_a_pair(self):
        tsub = T0Mpair(T0Mint(1), T0Mint(2))
        term = T0Mpsnd(T0Mvar("x"))
        self.assertEqual(t0erm_subst0(term, "x", tsub), T0Mpsnd(tsub))

    def test_under_lambda(self):
        # free x gets replaced
        term = T0Mlam("y", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        expected = T0Mlam("y", T0Mpair(T0Mint(7), T0Mvar("y")))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)
        # bound x doesn't
        term = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), term)
        self.assertEqual(t0erm_subst0(term, "y", T0Mint(7)),
                         T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mint(7))))

    def test_under_fix(self):
        body = T0Mpfst(T0Mpair(T0Mvar("f"), T0Mpair(T0Mvar("x"), T0Mvar("z"))))
        term = T0Mfix("f", "x", body)
        # z is free
        self.assertEqual(
            t0erm_subst0(term, "z", T0Mint(7)),
            T0Mfix("f", "x", T0Mpfst(T0Mpair(T0Mvar("f"), T0Mpair(T0Mvar("x"), T0Mint(7))))))
        # f and x are bound
        self.assertEqual(t0erm_subst0(term, "f", T0Mint(7)), term)
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), term)

    def test_inside_other_constructs(self):
        term = T0Mapp(T0Mpfst(T0Mvar("x")), T0Mif0(T0Mvar("x"), T0Mpair(T0Mvar("x"), T0Mint(0)),
                                                   T0Mop1("-", T0Mpsnd(T0Mvar("x")))))
        s = T0Mint(3)
        expected = T0Mapp(T0Mpfst(s), T0Mif0(s, T0Mpair(s, T0Mint(0)),
                                             T0Mop1("-", T0Mpsnd(s))))
        self.assertEqual(t0erm_subst0(term, "x", s), expected)


class TestEvaluatePairs(unittest.TestCase):
    def test_pair_of_values_is_a_value(self):
        for pair in [T0Mpair(T0Mint(1), T0Mint(2)),
                     T0Mpair(T0Mbtf(True), T0Mstr("a")),
                     T0Mpair(T0Mlam("x", DIV0), T0Mint(0))]:
            with self.subTest(pair=pair):
                self.assertEqual(ev(pair), pair)

    def test_components_are_evaluated(self):
        pair = T0Mpair(T0Mop2("*", T0Mint(2), T0Mint(3)), T0Mop2("+", T0Mint(2), T0Mint(3)))
        self.assertEqual(ev(pair), T0Mpair(T0Mint(6), T0Mint(5)))
        self.assertEqual(ev(T0Mpfst(pair)), T0Mint(6))
        self.assertEqual(ev(T0Mpsnd(pair)), T0Mint(5))

    def test_spec_example(self):
        term = T0Mpsnd(T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3))))
        self.assertEqual(ev(term), T0Mint(5))

    def test_nested_pairs(self):
        term = T0Mpair(T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(1), T0Mint(1))),
                       T0Mpair(T0Mint(3), T0Mpair(T0Mint(4), T0Mint(5))))
        self.assertEqual(ev(term), T0Mpair(T0Mpair(T0Mint(1), T0Mint(2)),
                                           T0Mpair(T0Mint(3), T0Mpair(T0Mint(4), T0Mint(5)))))
        self.assertEqual(ev(T0Mpfst(T0Mpfst(term))), T0Mint(1))
        self.assertEqual(ev(T0Mpsnd(T0Mpfst(term))), T0Mint(2))
        self.assertEqual(ev(T0Mpsnd(T0Mpsnd(T0Mpsnd(term)))), T0Mint(5))
        self.assertEqual(ev(T0Mpfst(T0Mpsnd(T0Mpsnd(term)))), T0Mint(4))

    def test_mixed_kinds_of_values(self):
        fn = T0Mlam("x", T0Mop2("+", T0Mvar("x"), T0Mint(1)))
        term = T0Mpair(fn, T0Mpair(T0Mstr("s"), T0Mbtf(False)))
        self.assertEqual(ev(T0Mpfst(T0Mpsnd(term))), T0Mstr("s"))
        self.assertEqual(ev(T0Mpsnd(T0Mpsnd(term))), T0Mbtf(False))
        self.assertEqual(ev(T0Mapp(T0Mpfst(term), T0Mint(41))), T0Mint(42))

    def test_pair_of_pairs_projection_is_a_pair(self):
        inner = T0Mpair(T0Mint(1), T0Mint(2))
        self.assertEqual(ev(T0Mpfst(T0Mpair(inner, T0Mint(9)))), inner)

    def test_function_accepting_a_pair(self):
        # swap = lambda p. (snd p, fst p)
        swap = T0Mlam("p", T0Mpair(T0Mpsnd(T0Mvar("p")), T0Mpfst(T0Mvar("p"))))
        term = T0Mapp(swap, T0Mpair(T0Mint(1), T0Mstr("a")))
        self.assertEqual(ev(term), T0Mpair(T0Mstr("a"), T0Mint(1)))
        # add = lambda p. fst p + snd p
        add = T0Mlam("p", T0Mop2("+", T0Mpfst(T0Mvar("p")), T0Mpsnd(T0Mvar("p"))))
        self.assertEqual(ev(T0Mapp(add, T0Mpair(T0Mint(20), T0Mint(22)))), T0Mint(42))

    def test_function_returning_a_pair(self):
        # dup = lambda x. (x, x)
        dup = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("x")))
        term = T0Mapp(dup, T0Mop2("+", T0Mint(1), T0Mint(2)))
        self.assertEqual(ev(term), T0Mpair(T0Mint(3), T0Mint(3)))
        self.assertEqual(ev(T0Mapp(dup, T0Mpair(T0Mint(1), T0Mint(2)))),
                         T0Mpair(T0Mpair(T0Mint(1), T0Mint(2)), T0Mpair(T0Mint(1), T0Mint(2))))

    def test_curried_function_over_pairs(self):
        # (lambda p. lambda q. (fst p, snd q)) (1,2) (3,4)
        f = T0Mlam("p", T0Mlam("q", T0Mpair(T0Mpfst(T0Mvar("p")), T0Mpsnd(T0Mvar("q")))))
        term = T0Mapp(T0Mapp(f, T0Mpair(T0Mint(1), T0Mint(2))), T0Mpair(T0Mint(3), T0Mint(4)))
        self.assertEqual(ev(term), T0Mpair(T0Mint(1), T0Mint(4)))

    def test_recursion_over_pairs(self):
        # sum(p) = if fst p <= 0 then snd p else sum(fst p - 1, snd p + fst p)
        p = T0Mvar("p")
        total = T0Mfix("sum", "p", T0Mif0(
            T0Mop2("<=", T0Mpfst(p), T0Mint(0)),
            T0Mpsnd(p),
            T0Mapp(T0Mvar("sum"), T0Mpair(T0Mop2("-", T0Mpfst(p), T0Mint(1)),
                                          T0Mop2("+", T0Mpsnd(p), T0Mpfst(p)))),
        ))
        self.assertEqual(ev(T0Mapp(total, T0Mpair(T0Mint(10), T0Mint(0)))), T0Mint(55))

    def test_pair_as_a_list(self):
        # nth over a list made of nested pairs
        lst = T0Mpair(T0Mint(10), T0Mpair(T0Mint(20), T0Mpair(T0Mint(30), T0Mint(0))))
        nth = T0Mfix("nth", "l", T0Mlam("i", T0Mif0(
            T0Mop2("==", T0Mvar("i"), T0Mint(0)),
            T0Mpfst(T0Mvar("l")),
            T0Mapp(T0Mapp(T0Mvar("nth"), T0Mpsnd(T0Mvar("l"))),
                   T0Mop2("-", T0Mvar("i"), T0Mint(1))))))
        for i, expected in enumerate([10, 20, 30]):
            with self.subTest(i=i):
                self.assertEqual(ev(T0Mapp(T0Mapp(nth, lst), T0Mint(i))), T0Mint(expected))
        with self.assertRaises(TypeError):  # past the end
            ev(T0Mapp(T0Mapp(nth, lst), T0Mint(3)))

    def test_substitution_during_application(self):
        term = T0Mapp(
            T0Mlam("p", T0Mlam("y", T0Mpair(T0Mpsnd(T0Mvar("p")),
                                            T0Mop2("+", T0Mpfst(T0Mvar("p")), T0Mvar("y"))))),
            T0Mpair(T0Mint(1), T0Mint(2)))
        self.assertEqual(ev(T0Mapp(term, T0Mint(10))), T0Mpair(T0Mint(2), T0Mint(11)))

    def test_pair_in_conditional(self):
        term = T0Mif0(T0Mpfst(T0Mpair(T0Mbtf(False), T0Mint(0))),
                      T0Mint(1), T0Mpsnd(T0Mpair(T0Mint(0), T0Mint(2))))
        self.assertEqual(ev(term), T0Mint(2))


class TestProjectionErrors(unittest.TestCase):
    def test_projection_of_non_pair(self):
        for value in [T0Mint(1), T0Mbtf(True), T0Mstr("s"), T0Mlam("x", T0Mvar("x")),
                      T0Mfix("f", "x", T0Mvar("x"))]:
            for proj in (T0Mpfst, T0Mpsnd):
                with self.subTest(proj=proj.__name__, value=value):
                    with self.assertRaises(TypeError):
                        ev(proj(value))

    def test_projection_of_computed_non_pair(self):
        for proj in (T0Mpfst, T0Mpsnd):
            with self.subTest(proj=proj.__name__):
                with self.assertRaises(TypeError):
                    ev(proj(T0Mop2("+", T0Mint(1), T0Mint(2))))

    def test_projection_past_the_pair(self):
        with self.assertRaises(TypeError):
            ev(T0Mpfst(T0Mpsnd(T0Mpair(T0Mint(1), T0Mint(2)))))
        with self.assertRaises(TypeError):
            ev(T0Mpsnd(T0Mpfst(T0Mpair(T0Mint(1), T0Mint(2)))))

    def test_operand_errors_propagate(self):
        for proj in (T0Mpfst, T0Mpsnd):
            with self.assertRaises(ZeroDivisionError):
                ev(proj(DIV0))


class TestEvaluationOrder(unittest.TestCase):
    def test_unselected_component_is_evaluated(self):
        with self.assertRaises(ZeroDivisionError):
            ev(T0Mpfst(T0Mpair(T0Mint(1), DIV0)))
        with self.assertRaises(ZeroDivisionError):
            ev(T0Mpsnd(T0Mpair(DIV0, T0Mint(1))))

    def test_pair_alone_evaluates_both(self):
        with self.assertRaises(ZeroDivisionError):
            ev(T0Mpair(T0Mint(1), DIV0))
        with self.assertRaises(ZeroDivisionError):
            ev(T0Mpair(DIV0, T0Mint(1)))

    def test_left_to_right(self):
        # whichever error is on the left should win
        bad_type = T0Mop1("-", T0Mstr("bad"))
        with self.assertRaises(ZeroDivisionError):
            ev(T0Mpair(DIV0, bad_type))
        with self.assertRaises(TypeError):
            ev(T0Mpair(bad_type, DIV0))

    def test_left_to_right_in_nested_pairs(self):
        bad_type = T0Mop1("-", T0Mstr("bad"))
        with self.assertRaises(ZeroDivisionError):
            ev(T0Mpair(T0Mpair(T0Mint(1), DIV0), T0Mpair(bad_type, T0Mint(2))))
        with self.assertRaises(TypeError):
            ev(T0Mpair(T0Mpair(T0Mint(1), bad_type), T0Mpair(DIV0, T0Mint(2))))

    def test_unused_pair_argument_is_still_evaluated(self):
        term = T0Mapp(T0Mlam("p", T0Mint(0)), T0Mpair(T0Mint(1), DIV0))
        with self.assertRaises(ZeroDivisionError):
            ev(term)

    def test_lambda_body_pair_is_not_evaluated_early(self):
        term = T0Mpair(T0Mlam("x", T0Mpair(DIV0, DIV0)), T0Mint(0))
        self.assertEqual(ev(term), term)


if __name__ == "__main__":
    unittest.main(verbosity=2)
