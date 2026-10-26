"""Observers / decoders (ACC-11, ACC-12, OBS-01 .. OBS-03)."""
import unittest

from helpers import EXEC, OBS, compiled_answer
from church import ADD, EQ, FALSE, MUL, NUM, PAIR, SUCC, TRUE, apps, lams
from evaluator import evaluate
from observe import (BOOL, MALFORMED, NAT, OBS_EXHAUSTED, OK, observe,
                     observe_bool, observe_nat, pair_kind)
from source_syntax import D0Ebtf, D0Eint, D0Epair
from target import App, Lam, Var

v = Var
OMEGA_HALF = lams("x", App(v("x"), v("x")))


def value_of(term):
    r = evaluate(term, EXEC)
    assert r.completed
    return r.value


class NaturalObserverTests(unittest.TestCase):
    def test_literals(self):
        for k in range(6):
            o = observe_nat(NUM(k), OBS)
            self.assertEqual((o.status, o.value), (OK, k))

    def test_alpha_renamed_literal(self):
        two = lams("succ", "zero", App(v("succ"), App(v("succ"), v("zero"))))
        self.assertEqual(observe_nat(two, OBS).value, 2)

    def test_computed_values_with_inner_redexes(self):
        val = value_of(apps(ADD, NUM(2), apps(MUL, NUM(2), NUM(3))))
        self.assertIsInstance(val, Lam)
        self.assertEqual(observe_nat(val, OBS).value, 8)
        self.assertEqual(observe_nat(value_of(App(SUCC, NUM(4))), OBS).value, 5)

    def test_malformed(self):
        o = observe_nat(TRUE, OBS)                    # TRUE STEP BASE = STEP
        self.assertEqual(o.status, MALFORMED)
        self.assertIsNone(o.value)
        o = observe_nat(lams("a", "b", v("a")), OBS)
        self.assertEqual(o.status, MALFORMED)

    def test_exhaustion_is_not_a_value(self):
        o = observe_nat(NUM(3), 0)
        self.assertEqual((o.status, o.value, o.steps), (OBS_EXHAUSTED, None, 0))
        # exactly enough budget succeeds; one less is exhaustion
        need = observe_nat(NUM(3), OBS).steps
        self.assertEqual(observe_nat(NUM(3), need).status, OK)
        self.assertEqual(observe_nat(NUM(3), need - 1).status, OBS_EXHAUSTED)

    def test_diverging_observation(self):
        weird = lams("s", "z", App(OMEGA_HALF, OMEGA_HALF))
        o = observe_nat(weird, 500)
        self.assertEqual((o.status, o.steps), (OBS_EXHAUSTED, 500))


class BooleanObserverTests(unittest.TestCase):
    def test_literals(self):
        self.assertIs(observe_bool(TRUE, OBS).value, True)
        self.assertIs(observe_bool(FALSE, OBS).value, False)

    def test_alpha_renamed_and_computed(self):
        self.assertIs(observe_bool(lams("yes", "no", v("yes")), OBS).value, True)
        self.assertIs(observe_bool(value_of(apps(EQ, NUM(2), NUM(2))), OBS).value, True)

    def test_malformed(self):
        self.assertEqual(observe_bool(NUM(2), OBS).status, MALFORMED)
        self.assertEqual(observe_bool(lams("x", v("x")), OBS).status, MALFORMED)

    def test_exhaustion(self):
        self.assertEqual(observe_bool(TRUE, 1).status, OBS_EXHAUSTED)

    def test_zero_needs_a_kind(self):
        # NUM(0) and FALSE are the same term; the requested kind decides.
        self.assertEqual(observe(NUM(0), NAT, OBS).value, 0)
        self.assertIs(observe(NUM(0), BOOL, OBS).value, False)
        self.assertEqual(observe(FALSE, NAT, OBS).value, 0)


class PairObserverTests(unittest.TestCase):
    def test_nested_pair_acc12(self):
        src = D0Epair(D0Epair(D0Eint(2), D0Ebtf(True)), D0Eint(3))
        kind = pair_kind(pair_kind(NAT, BOOL), NAT)
        self.assertEqual(compiled_answer(src, kind), ((2, True), 3))

    def test_pair_of_computed_values(self):
        val = value_of(apps(PAIR, apps(ADD, NUM(1), NUM(1)), apps(EQ, NUM(1), NUM(2))))
        o = observe(val, pair_kind(NAT, BOOL), OBS)
        self.assertEqual((o.status, o.value), (OK, (2, False)))

    def test_projection_exhaustion(self):
        bad_pair = lams("p", App(OMEGA_HALF, OMEGA_HALF))   # a value, but not a pair
        o = observe(bad_pair, pair_kind(NAT, NAT), 300)
        self.assertEqual((o.status, o.steps), (OBS_EXHAUSTED, 300))

    def test_component_malformed(self):
        val = value_of(apps(PAIR, TRUE, NUM(1)))
        o = observe(val, pair_kind(NAT, NAT), OBS)
        self.assertEqual(o.status, MALFORMED)

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            observe(NUM(1), "string", OBS)


if __name__ == "__main__":
    unittest.main()
