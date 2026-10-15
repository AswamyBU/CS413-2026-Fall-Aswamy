import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
import lambda1 as L
from backend import Backend, read_source, perform
from model import Model
from controller import Controller

class LanguageTests(unittest.TestCase):
    def test_scope_and_all_constructors(self):
        cases = {
            'D0Eint(2)': set(), 'D0Ebtf(True)': set(), 'D0Evar("x")': {'x'},
            'D0Eop1("+1", D0Evar("x"))': {'x'},
            'D0Eop2("+", D0Evar("x"), D0Evar("x"))': {'x'},
            'D0Elam("x", D0Elam("y", D0Epair(D0Evar("x"), D0Evar("z"))))': {'z'},
            'D0Efix("f", "x", D0Eapp(D0Evar("f"), D0Evar("x")))': set(),
            'D0Eapp(D0Evar("f"), D0Evar("x"))': {'f','x'},
            'D0Eif0(D0Evar("a"), D0Evar("b"), D0Evar("c"))': {'a','b','c'},
            'D0Elet("x", D0Evar("x"), D0Evar("x"))': {'x'},
            'D0Epair(D0Evar("a"), D0Evar("b"))': {'a','b'},
            'D0Epfst(D0Evar("a"))': {'a'}, 'D0Epsnd(D0Evar("a"))': {'a'},
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                result=L.d0exp_fvset(read_source(source))
                self.assertIsInstance(result,frozenset)
                self.assertEqual(result,expected)

    def test_reader_rejects_python_and_bad_types(self):
        for source in ['__import__("os").system("pwd")','D0Eint(True)','D0Evar(1)','D0Eint(1+2)','D0Eint(arg1=2)','[D0Eint(2)]','D0E000()', '']:
            with self.subTest(source=source), self.assertRaises((ValueError,SyntaxError)):
                read_source(source)
        self.assertEqual(read_source('# comment\nD0Eint(-2)').arg1,-2)

    def test_real_examples_and_base_cases(self):
        for name, expected in [('Arithmetic',42),('Factorial',120),('Fibonacci',55)]:
            source=Path(f'examples/{name}.lambda').read_text()
            self.assertEqual(Backend().run('interpret',source),{'outcome':'success','text':f'D0Vint(arg1={expected})'})
            if name!='Arithmetic':
                for n in [0,1]:
                    base=source.rsplit('D0Eint(',1)[0]+f'D0Eint({n}))'
                    self.assertEqual(perform('interpret',base)['text'],f'D0Vint(arg1={1 if name=="Factorial" else n})')

    def test_lint_does_not_evaluate_and_errors(self):
        source='D0Eop2("/", D0Eint(1), D0Eint(0))'
        with patch.object(L,'d0exp_evaluate',side_effect=AssertionError('must not evaluate')):
            self.assertEqual(perform('lint',source)['outcome'],'success')
        self.assertEqual(perform('interpret',source)['outcome'],'runtime_error')
        self.assertEqual(perform('interpret','D0Eint(')['outcome'],'input_error')
        self.assertEqual(perform('lint','D0Epair(D0Evar("z"), D0Evar("a"))')['text'],'Undeclared variables: a, z')
        self.assertEqual(perform('interpret','D0Epair(D0Eint(1), D0Evar("x"))')['outcome'],'runtime_error')

    def test_timeout(self):
        with patch('backend.subprocess.run',side_effect=subprocess.TimeoutExpired('worker',3)):
            self.assertIn('3-second',Backend().run('interpret','D0Eint(1)')['text'])

class StateTests(unittest.TestCase):
    def test_revision_and_rejection(self):
        m=Model();m.apply('D0Eint(1)','Manual')
        for source in ['','  ','x'*65537]:
            with self.assertRaises(ValueError):m.apply(source,'Bad')
            self.assertEqual(m.source,'D0Eint(1)');self.assertEqual(m.revision,1)
        m.results.append({'text':'old'});m.artifact='old'
        m.apply('D0Eint(2)','Replacement')
        self.assertEqual(m.revision,2);self.assertEqual(m.results,[]);self.assertIsNone(m.artifact)

    def test_dispatch_failure_busy_and_retry(self):
        class Fake:
            fail=True
            def run(self,op,source):
                self.args=(op,source)
                with self_test.assertRaises(ValueError):c.apply('D0Eint(4)','Busy')
                with self_test.assertRaises(ValueError):c.run('lint')
                if self.fail:raise OSError()
                return {'outcome':'success','text':'ok'}
        self_test=self;fake=Fake();c=Controller(fake)
        with self.assertRaises(ValueError):c.run('lint')
        c.apply('D0Eint(3)','Manual')
        self.assertEqual(c.run('interpret')['results'][-1]['outcome'],'backend_error')
        self.assertFalse(c.state()['busy']);fake.fail=False
        self.assertEqual(c.run('lint')['results'][-1]['outcome'],'success')
        self.assertEqual(fake.args,('lint','D0Eint(3)'))

    def test_placeholders_and_execute(self):
        c=Controller();c.apply('D0Eint(1)','Manual')
        for operation in ['typecheck','compile']:
            result=c.run(operation)['results'][-1]
            self.assertEqual(result['outcome'],'not_implemented');self.assertEqual(result['revision'],1)
        self.assertIsNone(c.state()['artifact'])
        with self.assertRaises(ValueError):c.run('execute')

if __name__=='__main__':unittest.main()
