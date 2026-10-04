"""Restricted reader for LAMBDA constructor expressions.

The input format is a single Python *expression* built only from the
d0exp constructors in lambda1.py, e.g.

    D0Eop2("+", D0Eint(20), D0Eint(22))   # comments are allowed

The text is parsed with ``ast.parse(mode="eval")`` and the resulting syntax
tree is walked by hand.  Nothing is ever passed to ``eval``/``exec``: every
node must be a call to a known constructor, a string/integer/boolean literal,
or a negated integer literal.  Each argument is checked against the
constructor's field kinds before the lambda1 object is built.
"""

import ast

import lambda1 as L

# Field kinds used in the schema below.
EXP = "exp"     # nested d0exp
VAR = "var"     # variable name (str)
INT = "int"     # integer literal (not bool)
BOOL = "bool"   # boolean literal
OP1 = "op1"     # unary operator name
OP2 = "op2"     # binary operator name

OP1_NAMES = frozenset({"+1", "-1"})
OP2_NAMES = frozenset({"+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!="})

# constructor name -> (class, [(field name, kind), ...])
SCHEMA: dict[str, tuple[type, list[tuple[str, str]]]] = {
    "D0Eint":  (L.D0Eint,  [("arg1", INT)]),
    "D0Ebtf":  (L.D0Ebtf,  [("arg1", BOOL)]),
    "D0Eop1":  (L.D0Eop1,  [("name", OP1), ("arg1", EXP)]),
    "D0Eop2":  (L.D0Eop2,  [("name", OP2), ("arg1", EXP), ("arg2", EXP)]),
    "D0Evar":  (L.D0Evar,  [("arg1", VAR)]),
    "D0Elam":  (L.D0Elam,  [("arg1", VAR), ("arg2", EXP)]),
    "D0Efix":  (L.D0Efix,  [("arg1", VAR), ("arg2", VAR), ("arg3", EXP)]),
    "D0Eapp":  (L.D0Eapp,  [("arg1", EXP), ("arg2", EXP)]),
    "D0Eif0":  (L.D0Eif0,  [("arg1", EXP), ("arg2", EXP), ("arg3", EXP)]),
    "D0Elet":  (L.D0Elet,  [("arg1", VAR), ("arg2", EXP), ("arg3", EXP)]),
    "D0Epair": (L.D0Epair, [("arg1", EXP), ("arg2", EXP)]),
    "D0Epfst": (L.D0Epfst, [("arg1", EXP)]),
    "D0Epsnd": (L.D0Epsnd, [("arg1", EXP)]),
}

# Nesting deeper than this is rejected so later recursive passes
# (d0exp_fvset, d0exp_evaluate) cannot blow the Python stack on input alone.
MAX_DEPTH = 200


class ReadError(Exception):
    """The source is not a valid constructor expression."""


def _where(node: ast.AST) -> str:
    return f"line {max(getattr(node, 'lineno', 1) - 1, 1)}, column {getattr(node, 'col_offset', -1) + 1}"


def read_d0exp(source: str) -> L.D0E000:
    """Parse ``source`` into a lambda1 d0exp or raise ReadError."""
    if not source.strip():
        raise ReadError("source is empty")
    # Wrapping in parentheses lets the expression span lines and be indented
    # (e.g. pasted from elsewhere); line numbers are shifted back by one.
    try:
        tree = ast.parse("(\n" + source + "\n)", mode="eval")
    except SyntaxError as exn:
        line = min(max((exn.lineno or 1) - 1, 1), source.count("\n") + 1)
        raise ReadError(f"syntax error at line {line}: {exn.msg}") from None
    except (RecursionError, MemoryError):
        raise ReadError("expression is too deeply nested") from None
    return _read_exp(tree.body, 1)


def _read_exp(node: ast.AST, depth: int) -> L.D0E000:
    if depth > MAX_DEPTH:
        raise ReadError(f"expression nesting exceeds {MAX_DEPTH} levels")
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise ReadError(f"expected a d0exp constructor call at {_where(node)}")
    name = node.func.id
    if name not in SCHEMA:
        raise ReadError(f"unknown constructor {name!r} at {_where(node)}")
    cls, fields = SCHEMA[name]
    if len(node.args) > len(fields):
        raise ReadError(f"{name} takes {len(fields)} argument(s), got {len(node.args)} "
                        f"at {_where(node)}")

    given: dict[str, ast.AST] = {}
    for (fname, _), arg in zip(fields, node.args):
        if isinstance(arg, ast.Starred):
            raise ReadError(f"*-arguments are not allowed at {_where(arg)}")
        given[fname] = arg
    field_names = [f for f, _ in fields]
    for kw in node.keywords:
        if kw.arg is None:
            raise ReadError(f"**-arguments are not allowed at {_where(node)}")
        if kw.arg not in field_names:
            raise ReadError(f"{name} has no field {kw.arg!r} at {_where(node)}")
        if kw.arg in given:
            raise ReadError(f"{name} field {kw.arg!r} given twice at {_where(node)}")
        given[kw.arg] = kw.value

    values = {}
    for fname, kind in fields:
        if fname not in given:
            raise ReadError(f"{name} is missing field {fname!r} at {_where(node)}")
        values[fname] = _read_field(name, fname, kind, given[fname], depth)
    return cls(**values)


def _read_field(ctor: str, fname: str, kind: str, node: ast.AST, depth: int):
    if kind == EXP:
        return _read_exp(node, depth + 1)

    value = _literal(node)
    what = f"{ctor}.{fname} at {_where(node)}"
    if kind == INT:
        if type(value) is not int:
            raise ReadError(f"{what}: expected an integer literal")
    elif kind == BOOL:
        if type(value) is not bool:
            raise ReadError(f"{what}: expected True or False")
    elif kind == VAR:
        if type(value) is not str or not value:
            raise ReadError(f"{what}: expected a non-empty variable-name string")
    elif kind == OP1:
        if value not in OP1_NAMES:
            raise ReadError(f"{what}: unary operator must be one of {sorted(OP1_NAMES)}")
    elif kind == OP2:
        if value not in OP2_NAMES:
            raise ReadError(f"{what}: binary operator must be one of {sorted(OP2_NAMES)}")
    return value


_NO_LITERAL = object()


def _literal(node: ast.AST):
    """Return a str/int/bool literal value, or a sentinel for anything else."""
    if isinstance(node, ast.Constant) and type(node.value) in (str, int, bool):
        return node.value
    if (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and type(node.operand.value) is int):
        return -node.operand.value
    return _NO_LITERAL
