"""Behavioral tests for lambda1_vp.py; no third-party dependencies."""
import dataclasses
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('lambda1_vp', HERE.parent / 'lambda1_vp.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
CASES = json.loads((HERE / 'cases.json').read_text())


def expression(data):
    kind, *args = data
    if kind == 'int':
        args = [int(args[0])]
    else:
        args = [expression(a) if isinstance(a, list) else a for a in args]
    return getattr(m, 'D0E' + kind)(*args)


def value(data):
    kind, *args = data
    if kind == 'unknown':
        return m.D0V000()
    if kind == 'int':
        return m.D0Vint(int(args[0]))
    if kind == 'btf':
        return m.D0Vbtf(args[0])
    if kind == 'pair':
        return m.D0Vpair(*(value(a) for a in args))
    raise ValueError(kind)


class InterpreterTests(unittest.TestCase):
    def test_environment_shadowing_and_immutability(self):
        tail = m.ENVcns('x', m.D0Vint(1), m.ENVnil())
        env = m.ENVcns('x', m.D0Vint(2), tail)
        self.assertEqual(m.d0env_search(env, 'x'), m.D0Vint(2))
        self.assertEqual(m.d0exp_evaluate(m.D0Evar('x'), tail), m.D0Vint(1))
        self.assertEqual(m.d0env_search(env, 'missing'), m.D0V000())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            env.arg1 = 'y'

    def test_visitors_can_be_reused_without_scope_leaks(self):
        visitor = m.EvaluateVisitor(m.ENVcns('x', m.D0Vint(3), m.ENVnil()))
        term = m.D0Elet('x', m.D0Eint(8), m.D0Evar('x'))
        self.assertEqual(term.accept(visitor), m.D0Vint(8))
        self.assertEqual(m.D0Evar('x').accept(visitor), m.D0Vint(3))
        self.assertEqual(m.D0Evar('x').accept(m.FreeVariableVisitor()), frozenset({'x'}))

    def test_closures_capture_environment(self):
        env = m.ENVcns('z', m.D0Vint(4), m.ENVnil())
        for term, cls in [(m.D0Elam('x', m.D0Evar('z')), m.D0Vlam),
                          (m.D0Efix('f', 'x', m.D0Evar('z')), m.D0Vfix)]:
            closure = m.d0exp_evaluate(term, env)
            self.assertIsInstance(closure, cls)
            self.assertIs(closure.arg1, env)
            self.assertIs(closure.arg2, term)

    def test_unsupported_expression(self):
        for operation in (m.d0exp_evaluate, m.d0exp_fvset):
            with self.assertRaises(TypeError):
                operation(m.D0E000())


def make_test(row):
    def test(self):
        term = expression(row['expr'])
        self.assertEqual(m.d0exp_fvset(term), frozenset(row['fv']))
        if 'error' in row:
            expected = ZeroDivisionError if row['error'] == 'division' else TypeError
            with self.assertRaises(expected):
                m.d0exp_evaluate(term)
        elif 'value' in row:
            self.assertEqual(m.d0exp_evaluate(term), value(row['value']))
    test.__doc__ = row['name']
    return test


for index, row in enumerate(CASES):
    setattr(InterpreterTests, f'test_case_{index:03d}', make_test(row))

if __name__ == '__main__':
    unittest.main()
