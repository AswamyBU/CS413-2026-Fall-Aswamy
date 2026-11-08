"""Tests for compiling LAMBDA expressions to Python (Python 3.12+)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lambda3 as L


class PythonCompilationTests(unittest.TestCase):
    def compile_and_run(self, source):
        expr, _ = L.d0exp_parse_and_typecheck(source)
        generated = L.d0exp_compile(expr)
        namespace = {}
        exec(generated, namespace)
        return expr, namespace["_lambda_result"], namespace

    def assert_compiled_matches_interpreter(self, source):
        expr, result, namespace = self.compile_and_run(source)
        interpreted = L.d0exp_evaluate(expr)
        self.assertEqual(
            namespace["_lambda_format"](result),
            L.d0val_format(interpreted),
        )

    def test_recursive_factorial(self):
        source = (
            "let fact : sint -> sint = "
            "fix fact(n: sint): sint => "
            "if n <= 1 then 1 else n * fact(n - 1) "
            "in fact(6) end"
        )
        expr, result, _ = self.compile_and_run(source)
        self.assertEqual(result, 720)
        self.assertEqual(L.d0exp_evaluate(expr), L.D0Vint(720))

    def test_signed_integer_type_name(self):
        expr, typ = L.d0exp_parse_and_typecheck('(1: sint)')
        self.assertIsInstance(typ, L.TSint)
        self.assertEqual(L.format_type(typ), 'sint')
        with self.assertRaises(L.TypeCheckError):
            L.d0exp_parse_and_typecheck('(1: int)')

    def test_closure_captures_lexical_binding(self):
        self.assert_compiled_matches_interpreter(
            "let offset = 7 "
            "add_offset = lam (x: sint) => x + offset "
            "in add_offset(35) end"
        )

    def test_tuples_lists_and_options(self):
        examples = (
            "let pair = (9, true) in (pair.0, pair.1) end",
            "let xs : List[sint] = list_cons(3, list_cons(4, list_nil())) "
            "in (list_head(xs), list_tail(xs), list_nilq(xs)) end",
            "let value : Optn[sint] = optn_cons(12) "
            "in (optn_nilq(value), optn_get(value)) end",
        )
        for source in examples:
            with self.subTest(source=source):
                self.assert_compiled_matches_interpreter(source)

    def test_compiled_conditional_only_evaluates_selected_branch(self):
        self.assert_compiled_matches_interpreter(
            "if true then 42 else 1 / 0"
        )

    def test_print_matches_interpreter_format(self):
        source = "print((true, list_cons(2, list_nil())))"
        expr, _ = L.d0exp_parse_and_typecheck(source)
        generated = L.d0exp_compile(expr)
        namespace = {}
        from contextlib import redirect_stdout
        from io import StringIO

        compiled_buffer = StringIO()
        with redirect_stdout(compiled_buffer):
            exec(generated, namespace)
        interpreted_buffer = StringIO()
        with redirect_stdout(interpreted_buffer):
            L.d0exp_evaluate(expr)
        self.assertEqual(compiled_buffer.getvalue(), interpreted_buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
