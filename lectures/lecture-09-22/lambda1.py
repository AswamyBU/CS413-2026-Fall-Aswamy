########################################################################
########################################################################
# Closure-based call-by-value LAMBDA interpreter.
# Requires Python 3.12 or later.
########################################################################
########################################################################
type nint = int
type sint = int
type strn = str
type dvar = str
########################################################################
from abc import ABC
from enum import Enum
from dataclasses import dataclass
from typing import \
    Generic, TypeVar, Callable
########################################################################
########################################################################
@dataclass
class D0E000(ABC):
    ctag = "D0E000"
    pass
type d0exp = D0E000
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
    ctag = "D0Elam"
#
@dataclass
class D0Efix(D0E000):
    arg1: dvar
    arg2: dvar
    arg3: d0exp
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
class D0Epair(D0E000):
    arg1: d0exp
    arg2: d0exp
    ctag = "D0Epair"
########################################################################
@dataclass
class D0Epfst(D0E000):
    arg1: d0exp
    ctag = "D0Epfst"
########################################################################
@dataclass
class D0Epsnd(D0E000):
    arg1: d0exp
    ctag = "D0Epsnd"
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
    def f0_D0Eop1(dexp: D0Eop1) -> d0val:
        name = dexp.name
        dexp1 = d0exp_evaluate(dexp.arg1, denv)
        match name:
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
    elif isinstance(dexp, D0Eop1): return f0_D0Eop1(dexp)
    elif isinstance(dexp, D0Eop2): return f0_D0Eop2(dexp)
    elif isinstance(dexp, D0Evar): return f0_D0Evar(dexp)
    elif isinstance(dexp, D0Eapp): return f0_D0Eapp(dexp)
    elif isinstance(dexp, D0Epair):
        # Call-by-value: evaluate both components, from left to right.
        dval1 = d0exp_evaluate(dexp.arg1, denv)
        dval2 = d0exp_evaluate(dexp.arg2, denv)
        return D0Vpair(dval1, dval2)
    elif isinstance(dexp, D0Epfst):
        dpair = d0exp_evaluate(dexp.arg1, denv)
        if not isinstance(dpair, D0Vpair):
            raise TypeError(f"D0Vpair(...) expected: {dpair}")
        return dpair.arg1
    elif isinstance(dexp, D0Epsnd):
        dpair = d0exp_evaluate(dexp.arg1, denv)
        if not isinstance(dpair, D0Vpair):
            raise TypeError(f"D0Vpair(...) expected: {dpair}")
        return dpair.arg2
    else:
        raise TypeError(f"d0exp_evaluate({dexp})")
#
########################################################################
########################################################################
