"""Restricted constructor reader and replaceable, bounded language adapter."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import lambda1 as lang

LIMIT = 65536
SCHEMA = {
    'D0Eint': (int,), 'D0Ebtf': (bool,), 'D0Evar': (str,),
    'D0Eop1': (str, 'expr'), 'D0Eop2': (str, 'expr', 'expr'),
    'D0Elam': (str, 'expr'), 'D0Efix': (str, str, 'expr'),
    'D0Eapp': ('expr', 'expr'), 'D0Eif0': ('expr', 'expr', 'expr'),
    'D0Elet': (str, 'expr', 'expr'), 'D0Epair': ('expr', 'expr'),
    'D0Epfst': ('expr',), 'D0Epsnd': ('expr',),
}

def read_source(source):
    if not source.strip() or len(source.encode('utf-8')) > LIMIT:
        raise ValueError('Source must contain 1–65,536 UTF-8 bytes.')
    def read(node, expected='expr'):
        if expected != 'expr':
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and expected is int and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int:
                return -node.operand.value
            if not isinstance(node, ast.Constant) or type(node.value) is not expected:
                raise ValueError(f'Expected a literal {expected.__name__}.')
            return node.value
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id not in SCHEMA:
            raise ValueError('Use only supported D0E constructor calls; Python code is not allowed.')
        schema = SCHEMA[node.func.id]
        if node.keywords or len(node.args) != len(schema):
            raise ValueError(f'{node.func.id} expects {len(schema)} positional arguments.')
        return getattr(lang, node.func.id)(*(read(n, t) for n, t in zip(node.args, schema)))
    return read(ast.parse(source.strip(), mode='eval').body)

def perform(operation, source):
    if operation in ('typecheck', 'compile'):
        return {'outcome': 'not_implemented', 'text': 'Type checking is not yet implemented.' if operation == 'typecheck' else 'Compilation is not yet implemented.'}
    try:
        expr = read_source(source)
    except (ValueError, SyntaxError, RecursionError) as error:
        return {'outcome': 'input_error', 'text': str(error)}
    try:
        if operation == 'lint':
            names = sorted(lang.d0exp_fvset(expr))
            return {'outcome': 'language_error' if names else 'success', 'text': 'Undeclared variables: ' + ', '.join(names) if names else 'No free variables found. The program is closed.'}
        if operation != 'interpret':
            raise ValueError('Unknown operation.')
        value = lang.d0exp_evaluate(expr, lang.ENVnil())
        def invalid(v):
            return type(v) is lang.D0V000 or isinstance(v, lang.D0Vpair) and (invalid(v.arg1) or invalid(v.arg2))
        if invalid(value):
            return {'outcome': 'runtime_error', 'text': 'Evaluation returned an undefined value (D0V000); check undeclared variables.'}
        return {'outcome': 'success', 'text': repr(value)}
    except Exception as error:
        return {'outcome': 'runtime_error', 'text': f'{type(error).__name__}: {error}'}

class Backend:
    def run(self, operation, source):
        try:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), operation], input=source, text=True, capture_output=True, timeout=3)
            if result.returncode:
                return {'outcome': 'backend_error', 'text': 'Language worker failed. Your source is preserved; try again.'}
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            return {'outcome': 'backend_error', 'text': 'Execution stopped after the 3-second time limit. Edit your program or retry.'}

if __name__ == '__main__':
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    print(json.dumps(perform(sys.argv[1], sys.stdin.read())))
