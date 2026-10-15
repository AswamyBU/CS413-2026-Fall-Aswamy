from __future__ import annotations

########################################################################
########################################################################
# Visitor-based, closure-based call-by-value LAMBDA interpreter.
# Expressions dispatch through accept; visitors implement each operation.
# Requires Python 3.12 or later.
########################################################################
########################################################################
type nint = int
type sint = int
type strn = str
type dvar = str
########################################################################
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

R = TypeVar("R")
########################################################################
########################################################################
@dataclass
class D0E000(ABC):
    ctag = "D0E000"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        raise TypeError(f"unsupported expression {type(self).__name__}")
type d0exp = D0E000
########################################################################
@dataclass
class D0Eint(D0E000):
    arg1: sint
    ctag = "D0Eint"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_int(self)
########################################################################
@dataclass
class D0Ebtf(D0E000):
    arg1: bool
    ctag = "D0Ebtf"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_btf(self)
########################################################################
@dataclass
class D0Eop1(D0E000):
    name: strn
    arg1: d0exp
    ctag = "D0Eop1"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_op1(self)
########################################################################
@dataclass
class D0Eop2(D0E000):
    name: strn
    arg1: d0exp
    arg2: d0exp
    ctag = "D0Eop2"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_op2(self)
########################################################################
@dataclass
class D0Evar(D0E000):
    arg1: dvar
    ctag = "D0Evar"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_var(self)
########################################################################
#
# lam x. body(x)
# fix f(x). body(f,x)
# 
@dataclass
class D0Elam(D0E000):
    arg1: dvar
    arg2: d0exp
    ctag = "D0Elam"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_lam(self)
#
@dataclass
class D0Efix(D0E000):
    arg1: dvar
    arg2: dvar
    arg3: d0exp
    ctag = "D0Efix"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_fix(self)
#
########################################################################
@dataclass
class D0Eapp(D0E000):
    arg1: d0exp
    arg2: d0exp
    ctag = "D0Eapp"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_app(self)
########################################################################
@dataclass
class D0Eif0(D0E000):
    arg1: d0exp
    arg2: d0exp
    arg3: d0exp
    ctag = "D0Eif0"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_if0(self)
########################################################################
@dataclass
class D0Elet(D0E000):
    arg1: dvar
    arg2: d0exp
    arg3: d0exp
    ctag = "D0Elet"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_let(self)
########################################################################
@dataclass
class D0Epair(D0E000):
    arg1: d0exp
    arg2: d0exp
    ctag = "D0Epair"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_pair(self)
########################################################################
@dataclass
class D0Epfst(D0E000):
    arg1: d0exp
    ctag = "D0Epfst"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_pfst(self)
########################################################################
@dataclass
class D0Epsnd(D0E000):
    arg1: d0exp
    ctag = "D0Epsnd"

    def accept(self, visitor: D0ExpVisitor[R]) -> R:
        return visitor.visit_psnd(self)
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
@dataclass\
(frozen=True)
class ENVnil(ENV000):
    pass
########################################################################
@dataclass\
(frozen=True)
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
class D0Vpair(D0V000):
    arg1: d0val
    arg2: d0val
    ctag = "D0Vpair"
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
class D0ExpVisitor(ABC, Generic[R]):
    """An operation on expressions, with one method per expression form."""

    @abstractmethod
    def visit_int(self, dexp: D0Eint) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_btf(self, dexp: D0Ebtf) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_op1(self, dexp: D0Eop1) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_op2(self, dexp: D0Eop2) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_var(self, dexp: D0Evar) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_lam(self, dexp: D0Elam) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_fix(self, dexp: D0Efix) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_app(self, dexp: D0Eapp) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_if0(self, dexp: D0Eif0) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_let(self, dexp: D0Elet) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_pair(self, dexp: D0Epair) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_pfst(self, dexp: D0Epfst) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_psnd(self, dexp: D0Epsnd) -> R:
        raise NotImplementedError


class FreeVariableVisitor(D0ExpVisitor[frozenset[dvar]]):
    """Compute free names without evaluating the expression."""

    def visit_int(self, dexp: D0Eint) -> frozenset[dvar]:
        return frozenset()

    def visit_btf(self, dexp: D0Ebtf) -> frozenset[dvar]:
        return frozenset()

    def visit_var(self, dexp: D0Evar) -> frozenset[dvar]:
        return frozenset({dexp.arg1})

    def visit_lam(self, dexp: D0Elam) -> frozenset[dvar]:
        return dexp.arg2.accept(self) - {dexp.arg1}

    def visit_fix(self, dexp: D0Efix) -> frozenset[dvar]:
        return dexp.arg3.accept(self) - {dexp.arg1, dexp.arg2}

    def visit_let(self, dexp: D0Elet) -> frozenset[dvar]:
        # The name is bound only in the body, not in the initializer.
        return dexp.arg2.accept(self) | (dexp.arg3.accept(self) - {dexp.arg1})

    def visit_if0(self, dexp: D0Eif0) -> frozenset[dvar]:
        return (dexp.arg1.accept(self) | dexp.arg2.accept(self)
                | dexp.arg3.accept(self))

    def visit_op1(self, dexp: D0Eop1) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_pfst(self, dexp: D0Epfst) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_psnd(self, dexp: D0Epsnd) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_op2(self, dexp: D0Eop2) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_app(self, dexp: D0Eapp) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_pair(self, dexp: D0Epair) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)


def d0exp_fvset(dexp: d0exp) -> frozenset[dvar]:
    """Return free names; lambda, fix, and let respect lexical binding."""
    return dexp.accept(FreeVariableVisitor())


def d0env_search(denv: d0env, dvar: dvar) -> d0val:
    while isinstance(denv, ENVcns):
        if dvar == denv.arg1:
            return denv.arg2
        denv = denv.arg3
    return D0V000()  # Preserve the original unbound-variable error sentinel.


class EvaluateVisitor(D0ExpVisitor[d0val]):
    """Evaluate in a lexical environment using left-to-right call by value.

    Entering a new scope creates a new visitor, leaving this environment intact.
    Closures capture their defining environment, not their caller's environment.
    """

    def __init__(self, denv: d0env = ENVnil()) -> None:
        self.denv = denv

    def visit_int(self, dexp: D0Eint) -> d0val:
        return D0Vint(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> d0val:
        return D0Vbtf(dexp.arg1)

    def visit_var(self, dexp: D0Evar) -> d0val:
        return d0env_search(self.denv, dexp.arg1)

    def visit_lam(self, dexp: D0Elam) -> d0val:
        return D0Vlam(self.denv, dexp)

    def visit_fix(self, dexp: D0Efix) -> d0val:
        return D0Vfix(self.denv, dexp)

    def visit_app(self, dexp: D0Eapp) -> d0val:
        dfun = dexp.arg1.accept(self)
        darg = dexp.arg2.accept(self)
        if isinstance(dfun, D0Vlam):
            dlam = dfun.arg2
            denv = ENVcns(dlam.arg1, darg, dfun.arg1)
            return dlam.arg2.accept(EvaluateVisitor(denv))
        elif isinstance(dfun, D0Vfix):
            dfix = dfun.arg2
            denv = ENVcns(dfix.arg1, dfun, dfun.arg1)
            denv = ENVcns(dfix.arg2, darg, denv)
            return dfix.arg3.accept(EvaluateVisitor(denv))
        raise TypeError(f"f0_D0Eapp({dexp}): not D0Vlam/D0Vfix")

    def visit_if0(self, dexp: D0Eif0) -> d0val:
        cond = dexp.arg1.accept(self)
        if not isinstance(cond, D0Vbtf):
            raise TypeError(f"D0Vbtf(...) expected: {cond}")
        return (dexp.arg2 if cond.arg1 else dexp.arg3).accept(self)

    def visit_let(self, dexp: D0Elet) -> d0val:
        value = dexp.arg2.accept(self)
        denv = ENVcns(dexp.arg1, value, self.denv)
        return dexp.arg3.accept(EvaluateVisitor(denv))

    def visit_pair(self, dexp: D0Epair) -> d0val:
        first = dexp.arg1.accept(self)
        second = dexp.arg2.accept(self)
        return D0Vpair(first, second)

    def visit_pfst(self, dexp: D0Epfst) -> d0val:
        pair = dexp.arg1.accept(self)
        if not isinstance(pair, D0Vpair):
            raise TypeError(f"D0Vpair(...) expected: {pair}")
        return pair.arg1

    def visit_psnd(self, dexp: D0Epsnd) -> d0val:
        pair = dexp.arg1.accept(self)
        if not isinstance(pair, D0Vpair):
            raise TypeError(f"D0Vpair(...) expected: {pair}")
        return pair.arg2

    def visit_op1(self, dexp: D0Eop1) -> d0val:
        value = dexp.arg1.accept(self)
        if dexp.name not in ("+1", "-1"):
            raise TypeError(f"f0_D0Eop1({dexp}): not supported op1")
        if not isinstance(value, D0Vint):
            raise TypeError(f"D0Vint(...) expected: {value}")
        return D0Vint(value.arg1 + (1 if dexp.name == "+1" else -1))

    def visit_op2(self, dexp: D0Eop2) -> d0val:
        left = dexp.arg1.accept(self)
        right = dexp.arg2.accept(self)
        if dexp.name not in ("+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!="):
            raise TypeError(f"f0_D0Eop2({dexp}): not supported op2")
        if not isinstance(left, D0Vint):
            raise TypeError(f"D0Vint(...) expected: {left}")
        if not isinstance(right, D0Vint):
            raise TypeError(f"D0Vint(...) expected: {right}")
        match dexp.name:
            case "+":
                return D0Vint(left.arg1 + right.arg1)
            case "-":
                return D0Vint(left.arg1 - right.arg1)
            case "*":
                return D0Vint(left.arg1 * right.arg1)
            case "/":
                return D0Vint(left.arg1 // right.arg1)
            case "<":
                return D0Vbtf(left.arg1 < right.arg1)
            case ">":
                return D0Vbtf(left.arg1 > right.arg1)
            case "<=":
                return D0Vbtf(left.arg1 <= right.arg1)
            case ">=":
                return D0Vbtf(left.arg1 >= right.arg1)
            case "==":
                return D0Vbtf(left.arg1 == right.arg1)
            case "!=":
                return D0Vbtf(left.arg1 != right.arg1)


def d0exp_evaluate(dexp: d0exp, denv: d0env = ENVnil()) -> d0val:
    """Evaluate an expression, optionally supplying its free-variable bindings."""
    return dexp.accept(EvaluateVisitor(denv))
