"""Demonstrations and evaluation-order behaviour of compiled programs.

Obligations 5 (unselected divergence skipped; divergent arguments, let
initializers, and pair components exhaust) and 6 (all demonstrations,
nested pairs), plus ACC-08 and the demo command itself (DEM-01).
"""
import io
import unittest
from contextlib import redirect_stdout

import helpers
from helpers import BOOL, NAT, compiled_answer, compiled_exhausts, source_result
from examples import EXAMPLES, LOOP
from pipeline import run_program
from source_syntax import (D0Eapp, D0Ebtf, D0Eif0, D0Eint, D0Elam, D0Elet,
                           D0Eop1, D0Eop2, D0Epair, D0Epfst, D0Epsnd)
from target import is_pure

T, F = D0Ebtf(True), D0Ebtf(False)
n = D0Eint


class MandatoryDemonstrationTests(unittest.TestCase):
    def test_all_fourteen_present(self):
        ids = {e.ident for e in EXAMPLES if e.mandatory}
        self.assertEqual(ids, {f"DEMO-{i:02d}" for i in range(1, 15)})

    def test_every_example(self):
        for ex in EXAMPLES:
            with self.subTest(ex=ex.ident):
                report = run_program(ex.source, ex.kind, helpers.EXEC, helpers.OBS)
                self.assertTrue(is_pure(report.term))
                if ex.diverges:
                    self.assertFalse(report.execution.completed)
                    self.assertEqual(report.execution.steps, helpers.EXEC)
                    self.assertIsNone(report.observation)
                else:
                    self.assertTrue(report.execution.completed)
                    self.assertTrue(report.observation.ok)
                    self.assertEqual(report.decoded, ex.expected)
                    self.assertEqual(source_result(ex.source), ex.expected)

    def test_explicit_answers(self):
        table = {"DEMO-01": 14, "DEMO-02": 0, "DEMO-03": 7, "DEMO-04": 7,
                 "DEMO-05": 2, "DEMO-06": True, "DEMO-07": 4, "DEMO-08": 1,
                 "DEMO-10": 24, "DEMO-11": 5, "DEMO-13": False, "DEMO-14": True}
        by_id = {e.ident: e for e in EXAMPLES}
        for ident, want in table.items():
            with self.subTest(ident=ident):
                ex = by_id[ident]
                self.assertEqual(compiled_answer(ex.source, ex.kind), want)
        for ident in ("DEMO-09", "DEMO-12"):
            self.assertTrue(compiled_exhausts(by_id[ident].source))


class DelayedBranchTests(unittest.TestCase):
    """Only the selected branch / needed operand is evaluated."""

    def test_unselected_divergence_is_skipped(self):
        self.assertEqual(compiled_answer(D0Eif0(T, n(1), LOOP()), NAT), 1)
        self.assertEqual(compiled_answer(D0Eif0(F, LOOP(), n(2)), NAT), 2)
        self.assertIs(compiled_answer(D0Eop2("and", F, LOOP()), BOOL), False)
        self.assertIs(compiled_answer(D0Eop2("or", T, LOOP()), BOOL), True)

    def test_selected_divergence_exhausts(self):
        self.assertTrue(compiled_exhausts(D0Eif0(T, LOOP(), n(1))))
        self.assertTrue(compiled_exhausts(D0Eif0(F, n(1), LOOP())))
        self.assertTrue(compiled_exhausts(D0Eop2("and", T, LOOP())))
        self.assertTrue(compiled_exhausts(D0Eop2("or", F, LOOP())))
        self.assertTrue(compiled_exhausts(D0Eif0(LOOP(), n(1), n(2))))


class StrictPositionTests(unittest.TestCase):
    """Call-by-value: unused divergent values still diverge (ACC-08)."""

    def test_function_argument(self):
        self.assertTrue(compiled_exhausts(D0Eapp(D0Elam("x", n(0)), LOOP())))

    def test_let_initializer(self):
        self.assertTrue(compiled_exhausts(D0Elet("x", LOOP(), n(2))))

    def test_either_pair_component(self):
        self.assertTrue(compiled_exhausts(D0Epfst(D0Epair(n(2), LOOP()))))
        self.assertTrue(compiled_exhausts(D0Epsnd(D0Epair(LOOP(), T))))

    def test_operands(self):
        self.assertTrue(compiled_exhausts(D0Eop2("+", LOOP(), n(1))))
        self.assertTrue(compiled_exhausts(D0Eop2("*", n(0), LOOP())))
        self.assertTrue(compiled_exhausts(D0Eop2("==", n(0), LOOP())))
        self.assertTrue(compiled_exhausts(D0Eop1("not", LOOP())))


class DemoCommandTests(unittest.TestCase):
    def test_demo_runs_and_passes(self):
        import demo
        buf = io.StringIO()
        with redirect_stdout(buf):
            status = demo.main(["--no-save"])
        out = buf.getvalue()
        self.assertEqual(status, 0)
        self.assertIn(f"{len(EXAMPLES)}/{len(EXAMPLES)} examples matched", out)
        for word in ("source", "pure term", "execution", "observation",
                     "decoded", "expected", "budget"):
            self.assertIn(word, out)


if __name__ == "__main__":
    unittest.main()
