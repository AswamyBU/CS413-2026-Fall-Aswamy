########################################################################
########################################################################
# Closure-based call-by-value LAMBDA interpreter.
# Requires Python 3.12 or later.
########################################################################
from abc import ABC
from dataclasses import dataclass
########################################################################
type nint = int
type sint = int
type strn = str
type dvar = str
########################################################################
class Type(ABC):
    """A monomorphic simple type used by the static checker."""
    pass

@dataclass(frozen=True)
class TInt(Type):
    pass

@dataclass(frozen=True)
class TBool(Type):
    pass

@dataclass(frozen=True)
class TTuple(Type):
    items: tuple[Type, ...]

@dataclass(frozen=True)
class TFun(Type):
    argument: Type
    result: Type

@dataclass(frozen=True)
class TList(Type):
    element: Type

@dataclass(frozen=True)
class TOption(Type):
    element: Type

@dataclass(frozen=True)
class TMeta(Type):
    ident: int

type simple_type = TInt | TBool | TTuple | TFun | TList | TOption | TMeta

########################################################################
from enum import Enum
from basics0 import fnlist, fnlist_nil, fnlist_cons, fnlist_reverse
from basics0 import fnoptn, fnoptn_nil, fnoptn_cons
from typing import \
    Generic, TypeVar, Callable
########################################################################
########################################################################
@dataclass
class D0C000(ABC):
    ctag = "D0C000"
    pass
type d0cls = D0C000
########################################################################
@dataclass
class D0E000(ABC):
    ctag = "D0E000"
    pass
type d0exp = D0E000
########################################################################
@dataclass
class D0Cval(D0C000):
    arg1: dvar
    arg2: d0exp
    ann: simple_type
    ctag = "D0Cval"
########################################################################
@dataclass
class D0Eint(D0E000):
    arg1: sint
    ctag = "D0Eint"
########################################################################
@dataclass
class D0Ebtf(D0E000):
    arg1: bool
    ctag = "D0Ebtf"
########################################################################
@dataclass
class D0Eop0(D0E000):
    name: strn
    ctag = "D0Eop0"
########################################################################
@dataclass
class D0Eop1(D0E000):
    name: strn
    arg1: d0exp
    ctag = "D0Eop1"
########################################################################
@dataclass
class D0Eop2(D0E000):
    name: strn
    arg1: d0exp
    arg2: d0exp
    ctag = "D0Eop2"
########################################################################
@dataclass
class D0Evar(D0E000):
    arg1: dvar
    ctag = "D0Evar"
########################################################################
#
# lam x. body(x)
# fix f(x). body(f,x)
# 
@dataclass
class D0Elam(D0E000):
    arg1: dvar
    arg2: d0exp
    ann: simple_type
    ctag = "D0Elam"
#
@dataclass
class D0Efix(D0E000):
    arg1: dvar
    arg2: dvar
    arg3: d0exp
    ann: simple_type
    parameter_type: simple_type
    ctag = "D0Efix"
#
########################################################################
@dataclass
class D0Eapp(D0E000):
    arg1: d0exp
    arg2: d0exp
    ctag = "D0Eapp"
########################################################################
@dataclass
class D0Eif0(D0E000):
    arg1: d0exp
    arg2: d0exp
    arg3: d0exp
    ctag = "D0Eif0"
########################################################################
@dataclass
class D0Elet(D0E000):
    arg1: dvar
    arg2: d0exp
    arg3: d0exp
    ctag = "D0Elet"
########################################################################
@dataclass
class D0Elets(D0E000):
    arg1: fnlist[d0cls]
    arg2: d0exp
    ctag = "D0Elets"
########################################################################
@dataclass
class D0Etupl(D0E000):
    arg1: tuple[d0exp, ...]
    ctag = "D0Etupl"
########################################################################
@dataclass
class D0Eproj(D0E000):
    arg1: d0exp
    arg2: nint # Zero-based component index.
    ctag = "D0Eproj"
########################################################################
@dataclass
class D0V000(ABC):
    ctag = "D0V000"
    pass
type d0val = D0V000
########################################################################
@dataclass(frozen=True)
class ENV000(ABC):
    ctag = "ENV000"
    pass
type d0env = ENV000
########################################################################
@dataclass(frozen=True)
class ENVnil(ENV000):
    pass
########################################################################
@dataclass(frozen=True)
class ENVcns(ENV000):
    arg1: dvar
    arg2: d0val
    arg3: d0env
    ctag = "ENVcns"
########################################################################
@dataclass
class D0Vint(D0V000):
    arg1: sint
    ctag = "D0Vint"
########################################################################
@dataclass
class D0Vbtf(D0V000):
    arg1: bool
    ctag = "D0Vbtf"
########################################################################
@dataclass
class D0Voptn(D0V000):
    arg1: fnoptn[d0val]
    ctag = "D0Voptn"
########################################################################
@dataclass
class D0Vlist(D0V000):
    arg1: fnlist[d0val]
    ctag = "D0Vlist"
########################################################################
@dataclass
class D0Vtupl(D0V000):
    arg1: tuple[d0val, ...]
    ctag = "D0Vtupl"
########################################################################
@dataclass
class D0Vlam(D0V000):
    arg1: d0env
    arg2: D0Elam
    ctag = "D0Vlam"
########################################################################
@dataclass
class D0Vfix(D0V000):
    arg1: d0env
    arg2: D0Efix
    ctag = "D0Vfix"
########################################################################
########################################################################
#
def d0val_format(dval: d0val) -> str:
    """
    Format a value without exposing a closure's captured environment.
    """
    if isinstance(dval, D0Vint):
        return str(dval.arg1)
    if isinstance(dval, D0Vbtf):
        return 'true' if dval.arg1 else 'false'
    if isinstance(dval, D0Vtupl):
        body = ', '.join(d0val_format(value) for value in dval.arg1)
        return '(' + body + (',' if len(dval.arg1) == 1 else '') + ')'
    if isinstance(dval, D0Vlist):
        def elements():
            items = dval.arg1
            while isinstance(items, fnlist_cons):
                yield d0val_format(items.arg1)
                items = items.arg2
            if not isinstance(items, fnlist_nil):
                raise TypeError('Malformed list value')
        return '[' + ', '.join(elements()) + ']'
    if isinstance(dval, D0Voptn):
        if isinstance(dval.arg1, fnoptn_nil):
            return 'optn_nil()'
        if isinstance(dval.arg1, fnoptn_cons):
            return 'optn_cons(' + d0val_format(dval.arg1.arg1) + ')'
        raise TypeError('Malformed option value')
    if isinstance(dval, D0Vlam):
        return '<lam>'
    if isinstance(dval, D0Vfix):
        return '<fix>'
    raise TypeError(f'd0val_format: unsupported value {type(dval).__name__}')


def d0exp_fvset(dexp: d0exp) -> frozenset[dvar]:
    """
    Return the free variable names in dexp without evaluating it.

    Lambda binds its parameter; fix binds its name and parameter in its body.
    Let binds its name only in the body, not in its initializer.
    Lets binds each name in subsequent declarations and the body.
    """
    if isinstance(dexp, (D0Eint, D0Ebtf, D0Eop0)):
        return frozenset()
    elif isinstance(dexp, D0Evar):
        return frozenset({dexp.arg1})
    elif isinstance(dexp, D0Elam):
        return d0exp_fvset(dexp.arg2) - {dexp.arg1}
    elif isinstance(dexp, D0Efix):
        return d0exp_fvset(dexp.arg3) - {dexp.arg1, dexp.arg2}
    elif isinstance(dexp, D0Elet):
        return (d0exp_fvset(dexp.arg2) |
                (d0exp_fvset(dexp.arg3) - {dexp.arg1}))
    elif isinstance(dexp, D0Elets):
        fvars: frozenset[dvar] = frozenset()
        bound: set[dvar] = set()
        dcls = dexp.arg1
        while isinstance(dcls, fnlist_cons):
            dcl = dcls.arg1
            if not isinstance(dcl, D0Cval):
                raise TypeError(f"D0Cval(...) expected: {dcl}")
            fvars = fvars | (d0exp_fvset(dcl.arg2) - bound)
            bound.add(dcl.arg1)
            dcls = dcls.arg2
        if not isinstance(dcls, fnlist_nil):
            raise TypeError(f"fnlist_nil(...) expected: {dcls}")
        return fvars | (d0exp_fvset(dexp.arg2) - bound)
    elif isinstance(dexp, D0Etupl):
        return frozenset().union(*(d0exp_fvset(e) for e in dexp.arg1))
    elif isinstance(dexp, (D0Eop1, D0Eproj)):
        return d0exp_fvset(dexp.arg1)
    elif isinstance(dexp, (D0Eop2, D0Eapp)):
        return d0exp_fvset(dexp.arg1) | d0exp_fvset(dexp.arg2)
    elif isinstance(dexp, D0Eif0):
        return (d0exp_fvset(dexp.arg1) | d0exp_fvset(dexp.arg2) |
                d0exp_fvset(dexp.arg3))
    else:
        raise TypeError(f"d0exp_fvset: unsupported expression {type(dexp).__name__}")


def d0env_search(denv: d0env, dvar: dvar) -> d0val:
    while True:
        if isinstance(denv, ENVcns):
            if dvar == denv.arg1:
                return denv.arg2
            else:
                denv = denv.arg3; continue
        else:
            return D0V000() # HX: this indicates an error
    # end-of-(while True)
#
########################################################################
########################################################################
#
def d0exp_evaluate\
(dexp: d0exp, denv: d0env = ENVnil()) -> d0val:
    """
    [dexp] may contain free variables
    """
######
    def f0_D0Eif0(dexp: D0Eif0) -> d0val:
        dexp1 = d0exp_evaluate(dexp.arg1, denv)
        if not isinstance(dexp1, D0Vbtf):
            raise TypeError(f"D0Vbtf(...) expected: {dexp1}")
        if dexp1.arg1:
            return d0exp_evaluate(dexp.arg2, denv)
        else:
            return d0exp_evaluate(dexp.arg3, denv)
######
    def f0_D0Elet(dexp: D0Elet) -> d0val:
        # let x = value in body: evaluate value before binding x.
        dval = d0exp_evaluate(dexp.arg2, denv)
        denv_new = ENVcns(dexp.arg1, dval, denv)
        return d0exp_evaluate(dexp.arg3, denv_new)
######
    def f0_D0Elets(dexp: D0Elets) -> d0val:
        denv_new = denv
        dcls = dexp.arg1
        while isinstance(dcls, fnlist_cons):
            dcl = dcls.arg1
            if not isinstance(dcl, D0Cval):
                raise TypeError(f"D0Cval(...) expected: {dcl}")
            dval = d0exp_evaluate(dcl.arg2, denv_new)
            denv_new = ENVcns(dcl.arg1, dval, denv_new)
            dcls = dcls.arg2
        if not isinstance(dcls, fnlist_nil):
            raise TypeError(f"fnlist_nil(...) expected: {dcls}")
        return d0exp_evaluate(dexp.arg2, denv_new)
######
    def f0_D0Eop0(dexp: D0Eop0) -> d0val:
        match dexp.name:
            case "optn_nil":
                return D0Voptn(fnoptn_nil())
            case "list_nil":
                return D0Vlist(fnlist_nil())
            case _:
                raise TypeError(f"f0_D0Eop0({dexp}): not supported op0")
######
    def f0_D0Eop1(dexp: D0Eop1) -> d0val:
        name = dexp.name
        dexp1 = d0exp_evaluate(dexp.arg1, denv)
        match name:
            case "print":
                print(d0val_format(dexp1))
                return D0Vtupl(())
            case "optn_cons":
                return D0Voptn(fnoptn_cons(dexp1))
            case "optn_nilq" | "optn_get":
                if not isinstance(dexp1, D0Voptn):
                    raise TypeError(f"D0Voptn(...) expected: {dexp1}")
                if name == "optn_nilq":
                    return D0Vbtf(isinstance(dexp1.arg1, fnoptn_nil))
                if not isinstance(dexp1.arg1, fnoptn_cons):
                    raise ValueError("optn_get: nonempty option expected")
                return dexp1.arg1.arg1
            case "list_nilq":
                if not isinstance(dexp1, D0Vlist):
                    raise TypeError(f"D0Vlist(...) expected: {dexp1}")
                return D0Vbtf(isinstance(dexp1.arg1, fnlist_nil))
            case "list_head" | "list_tail":
                if not isinstance(dexp1, D0Vlist):
                    raise TypeError(f"D0Vlist(...) expected: {dexp1}")
                if not isinstance(dexp1.arg1, fnlist_cons):
                    raise ValueError(f"{name}: nonempty list expected")
                if name == "list_head":
                    return dexp1.arg1.arg1
                return D0Vlist(dexp1.arg1.arg2)
            case "+1":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                return D0Vint(dexp1.arg1+1)
            case "-1":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                return D0Vint(dexp1.arg1-1)
            case _:
                raise TypeError(f"f0_D0Eop1({dexp}): not supported op1")
######
    def f0_D0Eop2(dexp: D0Eop2) -> d0val:
        name = dexp.name
        dexp1 = d0exp_evaluate(dexp.arg1, denv)
        dexp2 = d0exp_evaluate(dexp.arg2, denv)
        match name:
            case "list_cons":
                if not isinstance(dexp2, D0Vlist):
                    raise TypeError(f"D0Vlist(...) expected: {dexp2}")
                return D0Vlist(fnlist_cons(dexp1, dexp2.arg1))
######
            case "+":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vint(dexp1.arg1+dexp2.arg1)
            case "-":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vint(dexp1.arg1-dexp2.arg1)
            case "*":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vint(dexp1.arg1*dexp2.arg1)
            case "/":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vint(dexp1.arg1//dexp2.arg1)
######
            case "<":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vbtf(dexp1.arg1 < dexp2.arg1)
            case ">":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vbtf(dexp1.arg1 > dexp2.arg1)
            case "<=":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vbtf(dexp1.arg1<=dexp2.arg1)
            case ">=":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vbtf(dexp1.arg1 >= dexp2.arg1)
            case "==":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vbtf(dexp1.arg1 == dexp2.arg1)
            case "!=":
                if not isinstance(dexp1, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp1}")
                if not isinstance(dexp2, D0Vint):
                    raise TypeError(f"D0Vint(...) expected: {dexp2}")
                return D0Vbtf(dexp1.arg1 != dexp2.arg1)
######
            case _:
                raise TypeError(f"f0_D0Eop2({dexp}): not supported op2")
######
    def f0_D0Evar(dexp: D0Evar) -> d0val:
        return d0env_search(denv, dexp.arg1)
######
    def f0_D0Eapp(dexp: D0Eapp) -> d0val:
        dfun = d0exp_evaluate(dexp.arg1, denv)
        darg = d0exp_evaluate(dexp.arg2, denv)
        if False:
            return None
        elif isinstance(dfun, D0Vlam):
            dlam = dfun.arg2
            denv_new = \
                ENVcns(dlam.arg1, darg, dfun.arg1)
            return d0exp_evaluate(dlam.arg2, denv_new)
        elif isinstance(dfun, D0Vfix):
            dfix = dfun.arg2
            denv_new0 = dfun.arg1
            denv_new1 = \
                ENVcns(dfix.arg1, dfun, denv_new0)
            denv_new2 = \
                ENVcns(dfix.arg2, darg, denv_new1)
            return d0exp_evaluate(dfix.arg3, denv_new2)
        else:
            raise TypeError(f"f0_D0Eapp({dexp}): not D0Vlam/D0Vfix")
######    
    if False:
        return D0V000()
    elif isinstance(dexp, D0Eint):
        return D0Vint(dexp.arg1)
    elif isinstance(dexp, D0Ebtf):
        return D0Vbtf(dexp.arg1)
    elif isinstance(dexp, D0Elam):
        return D0Vlam(denv, dexp)
    elif isinstance(dexp, D0Efix):
        return D0Vfix(denv, dexp)
    elif isinstance(dexp, D0Eif0): return f0_D0Eif0(dexp)
    elif isinstance(dexp, D0Elet): return f0_D0Elet(dexp)
    elif isinstance(dexp, D0Eop0): return f0_D0Eop0(dexp)
    elif isinstance(dexp, D0Eop1): return f0_D0Eop1(dexp)
    elif isinstance(dexp, D0Eop2): return f0_D0Eop2(dexp)
    elif isinstance(dexp, D0Evar): return f0_D0Evar(dexp)
    elif isinstance(dexp, D0Eapp): return f0_D0Eapp(dexp)
    elif isinstance(dexp, D0Elets): return f0_D0Elets(dexp)
    elif isinstance(dexp, D0Etupl):
        # Call-by-value: evaluate all components from left to right.
        return D0Vtupl(tuple(d0exp_evaluate(e, denv) for e in dexp.arg1))
    elif isinstance(dexp, D0Eproj):
        dtupl = d0exp_evaluate(dexp.arg1, denv)
        if not isinstance(dtupl, D0Vtupl):
            raise TypeError(f"D0Vtupl(...) expected: {dtupl}")
        if not 0 <= dexp.arg2 < len(dtupl.arg1):
            raise IndexError(f"Tuple projection index out of range: {dexp.arg2}")
        return dtupl.arg1[dexp.arg2]
    else:
        raise TypeError(f"d0exp_evaluate({dexp})")
#
########################################################################
########################################################################

# Concrete syntax: see SYNTAX.md.
import re
from collections.abc import Iterator


class LambdaSyntaxError(SyntaxError):
    """
    Malformed LAMBDA source, with a one-based line and column.
    """

@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    offset: int


_TOKEN_PATTERN = re.compile(
    r'(?P<space>\s+)|(?P<comment>\#[^\n]*)|'
    r'(?P<int>[0-9]+)|(?P<name>[A-Za-z_][A-Za-z_0-9]*)|'
    r'(?P<symbol>=>|->|<=|>=|==|!=|[()+*/<>=,.;:-]|\[|\])'
)
_KEYWORDS = frozenset({'lam', 'fix', 'if', 'then', 'else', 'let', 'in',
                       'end', 'true', 'false', 'list_nil', 'list_cons', 'list_nilq',
                       'list_head', 'list_tail', 'optn_nil', 'optn_cons',
                       'optn_nilq', 'optn_get', 'print'})


def _syntax_error(source: str, offset: int, message: str) -> LambdaSyntaxError:
    line = source.count('\n', 0, offset) + 1
    column = offset - source.rfind('\n', 0, offset)
    lines = source.split('\n')
    return LambdaSyntaxError(message, ('<lambda>', line, column, lines[line - 1]))


def _tokens(source: str) -> Iterator[_Token]:
    offset = 0
    while offset < len(source):
        match = _TOKEN_PATTERN.match(source, offset)
        if match is None:
            raise _syntax_error(source, offset, f'Unexpected character {source[offset]!r}')
        kind = match.lastgroup
        word = match.group()
        if kind not in ('space', 'comment'):
            if kind == 'symbol' or word in _KEYWORDS:
                kind = word
            yield _Token(kind, word, offset)
        offset = match.end()
    yield _Token('EOF', '', offset)


class _Parser:
    def __init__(self, source: str):
        self.source = source
        self.tokens = _tokens(source)
        self.token = next(self.tokens)

    def error(self, message: str) -> LambdaSyntaxError:
        return _syntax_error(self.source, self.token.offset, message)

    def take(self, kind: str) -> _Token:
        token = self.token
        if token.kind != kind:
            found = repr(token.text) if token.kind != 'EOF' else 'end of input'
            raise self.error(f'Expected {kind!r}, found {found}')
        if kind != 'EOF':
            self.token = next(self.tokens)
        return token

    def accept(self, kind: str) -> bool:
        if self.token.kind != kind:
            return False
        self.take(kind)
        return True

    def declarations(self, stop: str) -> fnlist[d0cls]:
        result = fnlist_nil()
        while self.token.kind != stop:
            name = self.take('name').text
            self.take(':')
            ann = self.type_expression()
            self.take('=')
            result = fnlist_cons(D0Cval(name, self.expression(), ann), result)
            self.accept(';')
        return fnlist_reverse(result)

    def type_expression(self) -> simple_type:
        left = self.type_atom()
        if self.accept('->'):
            return TFun(left, self.type_expression())
        return left

    def type_atom(self) -> simple_type:
        if self.accept('('):
            if self.accept(')'):
                return TTuple(())
            first = self.type_expression()
            if not self.accept(','):
                self.take(')')
                return first
            items = [first]
            while self.token.kind != ')':
                items.append(self.type_expression())
                if not self.accept(','):
                    break
            self.take(')')
            return TTuple(tuple(items))
        name = self.take('name').text
        if name == 'int':
            return TInt()
        if name == 'bool':
            return TBool()
        if name == 'unit':
            return TTuple(())
        if name in ('List', 'Option'):
            self.take('[')
            element = self.type_expression()
            self.take(']')
            return TList(element) if name == 'List' else TOption(element)
        raise self.error(f'Unknown type {name!r}; expected int, bool, List[T], Option[T], tuple, or function type')

    def expression(self) -> d0exp:
        if self.accept('lam'):
            self.take('(')
            name = self.take('name').text
            self.take(':')
            ann = self.type_expression()
            self.take(')')
            self.take('=>')
            return D0Elam(name, self.expression(), ann)
        if self.accept('fix'):
            name = self.take('name').text
            self.take('(')
            parameter = self.take('name').text
            self.take(':')
            parameter_type = self.type_expression()
            self.take(')')
            self.take(':')
            result_type = self.type_expression()
            self.take('=>')
            ann = TFun(parameter_type, result_type)
            return D0Efix(name, parameter, self.expression(), ann, parameter_type)
        if self.accept('if'):
            condition = self.expression()
            self.take('then')
            yes = self.expression()
            self.take('else')
            return D0Eif0(condition, yes, self.expression())
        if self.accept('let'):
            declarations = self.declarations('in')
            self.take('in')
            body = self.expression()
            self.take('end')
            return D0Elets(declarations, body)
        return self.comparison()

    def comparison(self) -> d0exp:
        result = self.additive()
        operators = ('<', '>', '<=', '>=', '==', '!=')
        if self.token.kind in operators:
            operator = self.take(self.token.kind).text
            result = D0Eop2(operator, result, self.additive())
            if self.token.kind in operators:
                raise self.error('Chained comparisons require parentheses')
        return result

    def additive(self) -> d0exp:
        result = self.multiplicative()
        while self.token.kind in ('+', '-'):
            operator = self.take(self.token.kind).text
            result = D0Eop2(operator, result, self.multiplicative())
        return result

    def multiplicative(self) -> d0exp:
        result = self.unary()
        while self.token.kind in ('*', '/'):
            operator = self.take(self.token.kind).text
            result = D0Eop2(operator, result, self.unary())
        return result

    def unary(self) -> d0exp:
        if self.accept('-'):
            return D0Eop2('-', D0Eint(0), self.unary())
        if self.accept('+'):
            return self.unary()
        return self.postfix()

    def postfix(self) -> d0exp:
        result = self.atom()
        while self.token.kind in ('(', '.'):
            if self.accept('.'):
                result = D0Eproj(result, int(self.take('int').text))
            else:
                result = D0Eapp(result, self.parenthesized())
        return result

    def parenthesized(self) -> d0exp:
        self.take('(')
        if self.accept(')'):
            return D0Etupl(())
        first = self.expression()
        if not self.accept(','):
            self.take(')')
            return first
        items = (first,)
        while self.token.kind != ')':
            items += (self.expression(),)
            if not self.accept(','):
                break
        self.take(')')
        return D0Etupl(items)

    def atom(self) -> d0exp:
        if self.token.kind in ('list_nilq', 'list_head', 'list_tail',
                               'optn_cons', 'optn_nilq', 'optn_get', 'print'):
            operator = self.take(self.token.kind).text
            self.take('(')
            operand = self.expression()
            self.take(')')
            return D0Eop1(operator, operand)
        if self.accept('list_cons'):
            self.take('(')
            head = self.expression()
            self.take(',')
            tail = self.expression()
            self.take(')')
            return D0Eop2('list_cons', head, tail)
        if self.token.kind in ('list_nil', 'optn_nil'):
            operator = self.take(self.token.kind).text
            self.take('(')
            self.take(')')
            return D0Eop0(operator)
        if self.token.kind == 'int':
            return D0Eint(int(self.take('int').text))
        if self.accept('true'):
            return D0Ebtf(True)
        if self.accept('false'):
            return D0Ebtf(False)
        if self.token.kind == 'name':
            return D0Evar(self.take('name').text)
        if self.token.kind == '(':
            return self.parenthesized()
        raise self.error('Expected an expression')


def d0exp_parse(source: str) -> d0exp:
    """
    Parse one complete expression; raise LambdaSyntaxError on invalid syntax.
    """
    parser = _Parser(source)
    result = parser.expression()
    parser.take('EOF')
    return result


def d0cls_parse(source: str) -> fnlist[d0cls]:
    """
    Parse zero or more sequential name = expression declarations.
    """
    parser = _Parser(source)
    result = parser.declarations('EOF')
    parser.take('EOF')
    return result


class TypeCheckError(TypeError):
    """A static typing error, reported before evaluating an expression."""


class _TypeSolver:
    def __init__(self):
        self.next_ident = 0
        self.substitution: dict[int, simple_type] = {}

    def fresh(self) -> TMeta:
        result = TMeta(self.next_ident)
        self.next_ident += 1
        return result

    def apply(self, typ: simple_type) -> simple_type:
        if isinstance(typ, TMeta) and typ.ident in self.substitution:
            result = self.apply(self.substitution[typ.ident])
            self.substitution[typ.ident] = result
            return result
        if isinstance(typ, TFun):
            return TFun(self.apply(typ.argument), self.apply(typ.result))
        if isinstance(typ, TTuple):
            return TTuple(tuple(self.apply(item) for item in typ.items))
        if isinstance(typ, TList):
            return TList(self.apply(typ.element))
        if isinstance(typ, TOption):
            return TOption(self.apply(typ.element))
        return typ

    def _occurs(self, ident: int, typ: simple_type) -> bool:
        typ = self.apply(typ)
        if isinstance(typ, TMeta):
            return typ.ident == ident
        if isinstance(typ, TFun):
            return self._occurs(ident, typ.argument) or self._occurs(ident, typ.result)
        if isinstance(typ, TTuple):
            return any(self._occurs(ident, item) for item in typ.items)
        if isinstance(typ, (TList, TOption)):
            return self._occurs(ident, typ.element)
        return False

    def unify(self, left: simple_type, right: simple_type, where: str) -> None:
        left, right = self.apply(left), self.apply(right)
        if left == right:
            return
        if isinstance(left, TMeta):
            if self._occurs(left.ident, right):
                raise TypeCheckError(f'{where}: infinite type {format_type(left)} = {format_type(right)}')
            self.substitution[left.ident] = right
            return
        if isinstance(right, TMeta):
            self.unify(right, left, where)
            return
        if isinstance(left, TFun) and isinstance(right, TFun):
            self.unify(left.argument, right.argument, where)
            self.unify(left.result, right.result, where)
            return
        if isinstance(left, TTuple) and isinstance(right, TTuple) and len(left.items) == len(right.items):
            for a, b in zip(left.items, right.items):
                self.unify(a, b, where)
            return
        if isinstance(left, TList) and isinstance(right, TList):
            self.unify(left.element, right.element, where)
            return
        if isinstance(left, TOption) and isinstance(right, TOption):
            self.unify(left.element, right.element, where)
            return
        raise TypeCheckError(f'{where}: expected {format_type(left)}, got {format_type(right)}')


def format_type(typ: simple_type) -> str:
    if isinstance(typ, TInt):
        return 'int'
    if isinstance(typ, TBool):
        return 'bool'
    if isinstance(typ, TMeta):
        return f"?t{typ.ident}"
    if isinstance(typ, TFun):
        left = format_type(typ.argument)
        if isinstance(typ.argument, TFun):
            left = f'({left})'
        return f'{left} -> {format_type(typ.result)}'
    if isinstance(typ, TTuple):
        if not typ.items:
            return 'unit'
        return '(' + ', '.join(format_type(item) for item in typ.items) + ')'
    if isinstance(typ, TList):
        return f'List[{format_type(typ.element)}]'
    if isinstance(typ, TOption):
        return f'Option[{format_type(typ.element)}]'
    raise TypeError(f'Unknown type: {typ!r}')


def d0exp_typecheck(dexp: d0exp) -> simple_type:
    """Statically check an AST and return its type (with container types resolved)."""
    solver = _TypeSolver()

    def check(expr: d0exp, env: dict[dvar, simple_type]) -> simple_type:
        if isinstance(expr, D0Eint):
            return TInt()
        if isinstance(expr, D0Ebtf):
            return TBool()
        if isinstance(expr, D0Evar):
            if expr.arg1 not in env:
                raise TypeCheckError(f"unbound variable {expr.arg1!r}")
            return env[expr.arg1]
        if isinstance(expr, D0Elam):
            inner = dict(env)
            inner[expr.arg1] = expr.ann
            return TFun(expr.ann, check(expr.arg2, inner))
        if isinstance(expr, D0Efix):
            declared = expr.ann
            expected_function = TFun(expr.parameter_type, solver.fresh())
            solver.unify(declared, expected_function, f"recursive function {expr.arg1!r}")
            inner = dict(env)
            inner[expr.arg1] = declared
            inner[expr.arg2] = expr.parameter_type
            body_type = check(expr.arg3, inner)
            solver.unify(expected_function.result, body_type, f"body of recursive function {expr.arg1!r}")
            return declared
        if isinstance(expr, D0Eif0):
            solver.unify(check(expr.arg1, env), TBool(), 'if condition')
            yes_type, no_type = check(expr.arg2, env), check(expr.arg3, env)
            solver.unify(yes_type, no_type, 'if branches')
            return yes_type
        if isinstance(expr, D0Elets):
            inner = dict(env)
            declarations = expr.arg1
            while isinstance(declarations, fnlist_cons):
                decl = declarations.arg1
                if not isinstance(decl, D0Cval):
                    raise TypeCheckError(f'expected value declaration, got {decl!r}')
                actual = check(decl.arg2, inner)
                solver.unify(decl.ann, actual, f"binding {decl.arg1!r}")
                inner[decl.arg1] = decl.ann
                declarations = declarations.arg2
            if not isinstance(declarations, fnlist_nil):
                raise TypeCheckError('malformed declaration list')
            return check(expr.arg2, inner)
        if isinstance(expr, D0Elet):
            raise TypeCheckError('unannotated D0Elet is not allowed; use an annotated let declaration')
        if isinstance(expr, D0Etupl):
            return TTuple(tuple(check(item, env) for item in expr.arg1))
        if isinstance(expr, D0Eproj):
            source = check(expr.arg1, env)
            source = solver.apply(source)
            if not isinstance(source, TTuple):
                raise TypeCheckError(f'tuple projection requires a tuple, got {format_type(source)}')
            if not 0 <= expr.arg2 < len(source.items):
                raise TypeCheckError(f'tuple index {expr.arg2} is out of range for {format_type(source)}')
            return source.items[expr.arg2]
        if isinstance(expr, D0Eapp):
            function_type = solver.apply(check(expr.arg1, env))
            argument_type = check(expr.arg2, env)
            result_type = solver.fresh()
            solver.unify(function_type, TFun(argument_type, result_type), 'function application')
            return result_type
        if isinstance(expr, D0Eif0):
            raise AssertionError('unreachable')
        if isinstance(expr, D0Eop0):
            if expr.name == 'list_nil':
                return TList(solver.fresh())
            if expr.name == 'optn_nil':
                return TOption(solver.fresh())
            raise TypeCheckError(f'unknown nullary operator {expr.name!r}')
        if isinstance(expr, D0Eop1):
            operand = check(expr.arg1, env)
            if expr.name in ('+1', '-1'):
                solver.unify(operand, TInt(), expr.name)
                return TInt()
            if expr.name == 'print':
                return TTuple(())
            if expr.name == 'optn_cons':
                return TOption(operand)
            if expr.name == 'optn_nilq':
                solver.unify(operand, TOption(solver.fresh()), 'optn_nilq')
                return TBool()
            if expr.name == 'optn_get':
                result = solver.fresh()
                solver.unify(operand, TOption(result), 'optn_get')
                return result
            if expr.name == 'list_nilq':
                solver.unify(operand, TList(solver.fresh()), 'list_nilq')
                return TBool()
            if expr.name == 'list_head':
                result = solver.fresh()
                solver.unify(operand, TList(result), 'list_head')
                return result
            if expr.name == 'list_tail':
                element = solver.fresh()
                solver.unify(operand, TList(element), 'list_tail')
                return TList(element)
            raise TypeCheckError(f'unknown unary operator {expr.name!r}')
        if isinstance(expr, D0Eop2):
            left, right = check(expr.arg1, env), check(expr.arg2, env)
            if expr.name in ('+', '-', '*', '/'):
                solver.unify(left, TInt(), expr.name)
                solver.unify(right, TInt(), expr.name)
                return TInt()
            if expr.name in ('<', '>', '<=', '>=', '==', '!='):
                solver.unify(left, TInt(), expr.name)
                solver.unify(right, TInt(), expr.name)
                return TBool()
            if expr.name == 'list_cons':
                element = solver.fresh()
                solver.unify(right, TList(element), 'list_cons tail')
                solver.unify(left, element, 'list_cons head')
                return TList(element)
            raise TypeCheckError(f'unknown binary operator {expr.name!r}')
        raise TypeCheckError(f'unsupported expression {type(expr).__name__}')

    result = check(dexp, {})
    return solver.apply(result)


def d0exp_parse_and_typecheck(source: str) -> tuple[d0exp, simple_type]:
    """Parse and type-check a source expression before it is evaluated."""
    expr = d0exp_parse(source)
    return expr, d0exp_typecheck(expr)


def d0cls_typecheck(declarations: fnlist[d0cls]) -> None:
    """Check a sequence returned by d0cls_parse, including its annotations."""
    d0exp_typecheck(D0Elets(declarations, D0Etupl(())))
