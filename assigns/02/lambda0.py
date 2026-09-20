########################################################################
########################################################################
# playing with lambda calculus
########################################################################
########################################################################
#
type nint = int
type sint = int
type strn = str
type tvar = strn
#
########################################################################
from abc import ABC
from enum import Enum
from dataclasses import dataclass
from typing import \
    Generic, TypeVar, Callable
########################################################################
@dataclass
class T0M000(ABC):
    ctag = "T0M000"
    pass
type t0erm = T0M000
########################################################################
@dataclass
class T0Mvar(T0M000):
    arg1: tvar
    ctag = "T0Mvar"
########################################################################
@dataclass
class T0Mlam(T0M000):
    arg1: tvar
    arg2: t0erm
    ctag = "T0Mlam"
@dataclass
class T0Mfix(T0M000):
    arg1: tvar
    arg2: tvar
    arg3: t0erm
    ctag = "T0Mfix"
########################################################################
@dataclass
class T0Mapp(T0M000):
    arg1: t0erm
    arg2: t0erm
    ctag = "T0Mapp"
########################################################################
@dataclass
class T0Mint(T0M000):
    arg1: sint
    ctag = "T0Mint"
@dataclass
class T0Mbtf(T0M000):
    arg1: bool
    ctag = "T0Mbtf"
@dataclass
class T0Mstr(T0M000):
    arg1: strn
    ctag = "T0Mstr"
########################################################################
@dataclass
class T0Mop1(T0M000):
    arg1: strn
    arg2: t0erm
    ctag = "T0Mop1"
@dataclass
class T0Mop2(T0M000):
    arg1: strn
    arg2: t0erm
    arg3: t0erm
    ctag = "T0Mop2"
########################################################################
@dataclass
class T0Mif0(T0M000):
    arg1: t0erm
    arg2: t0erm
    arg3: t0erm
    ctag = "T0Mif0"
########################################################################
########################################################################
@dataclass
class T0Mpair(T0M000): # pair
    arg1: t0erm
    arg2: t0erm
    ctag = "T0Mpair"
@dataclass
class T0Mpfst(T0M000): # fst projection
    arg1: t0erm
    ctag = "T0Mpfst"
@dataclass
class T0Mpsnd(T0M000): # 2nd projection
    arg1: t0erm
    ctag = "T0Mpsnd"
########################################################################
########################################################################
def t0erm_size(term: t0erm) -> sint:
    if False:
        return 0
    elif isinstance(term, T0Mint):
        return 1
    elif isinstance(term, T0Mbtf):
        return 1
    elif isinstance(term, T0Mstr):
        return 1
    elif isinstance(term, T0Mvar):
        return 1
    elif isinstance(term, T0Mlam):
        return 1 + t0erm_size(term.arg2)
    elif isinstance(term, T0Mfix):
        return 1 + t0erm_size(term.arg3)
    elif isinstance(term, T0Mapp):
        return 1 + t0erm_size(term.arg1) + t0erm_size(term.arg2)
    elif isinstance(term, T0Mop1):
        return 1 + t0erm_size(term.arg2)
    elif isinstance(term, T0Mop2):
        return 1 + t0erm_size(term.arg2) + t0erm_size(term.arg3)
    elif isinstance(term, T0Mif0):
        return 1 + t0erm_size(term.arg1) + t0erm_size(term.arg2) + t0erm_size(term.arg3)
    else:
        raise TypeError(f"t0erm_size({term})")
########################################################################
X = TypeVar("X")
type fvset = frozenset[strn]
########################################################################
def t0erm_fvset(term: t0erm) -> fvset:
    if False:
        return frozenset()
    elif isinstance(term, T0Mint):
        return frozenset()
    elif isinstance(term, T0Mbtf):
        return frozenset()
    elif isinstance(term, T0Mstr):
        return frozenset()
    elif isinstance(term, T0Mvar):
        return frozenset([term.arg1])
    elif isinstance(term, T0Mlam):
        return t0erm_fvset(term.arg2) - {term.arg1}
    elif isinstance(term, T0Mfix):
        return t0erm_fvset(term.arg3) - {term.arg1, term.arg2}
    elif isinstance(term, T0Mapp):
        return (t0erm_fvset(term.arg1) | t0erm_fvset(term.arg2))
    elif isinstance(term, T0Mop1):
        return t0erm_fvset(term.arg2)
    elif isinstance(term, T0Mop2):
        return (t0erm_fvset(term.arg2) | t0erm_fvset(term.arg3))
    elif isinstance(term, T0Mif0):
        return (t0erm_fvset(term.arg1) | t0erm_fvset(term.arg2) | t0erm_fvset(term.arg3))
    else:
        raise TypeError(f"t0erm_fvset({term})")
########################################################################
#
# HX-2026-08-25:
# [tsub] is assumed to be closed;
# therefore, no capturing is possible!
#
def t0erm_subst0\
(term: t0erm, x0: tvar, tsub: t0erm) -> t0erm:
    def subst0(term: t0erm) -> t0erm:
        if False:
            return None
        elif isinstance(term, T0Mint):
            return term
        elif isinstance(term, T0Mbtf):
            return term
        elif isinstance(term, T0Mstr):
            return term
        elif isinstance(term, T0Mvar):
            return tsub if x0 == term.arg1 else term
        elif isinstance(term, T0Mlam):
            x1 = term.arg1
            if x0 == x1:
                return term
            else:
                return T0Mlam(x1, subst0(term.arg2))
        elif isinstance(term, T0Mfix):
            f0 = term.arg1
            x1 = term.arg2
            if x0 == f0:
                return term
            elif x0 == x1:
                return term
            else:
                return T0Mfix(f0, x1, subst0(term.arg3))
        elif isinstance(term, T0Mapp):
            return T0Mapp(subst0(term.arg1), subst0(term.arg2))
        elif isinstance(term, T0Mop1):
            return T0Mop1(term.arg1, subst0(term.arg2))
        elif isinstance(term, T0Mop2):
            return T0Mop2(term.arg1, subst0(term.arg2), subst0(term.arg3))
        elif isinstance(term, T0Mif0):
            return T0Mif0(subst0(term.arg1), subst0(term.arg2), subst0(term.arg3))
        else:
            raise TypeError(f"subst0({term})")
    return subst0(term)
#
########################################################################
########################################################################
#
def t0erm_cbv_evaluate0(term: t0erm) -> t0erm:
    if False:
        return None
    elif isinstance(term, T0Mint): return term
    elif isinstance(term, T0Mbtf): return term
    elif isinstance(term, T0Mstr): return term
    elif isinstance(term, T0Mlam): return term
    elif isinstance(term, T0Mfix): return term
    elif isinstance(term, T0Mapp):
        t1 = t0erm_cbv_evaluate0(term.arg1)
        t2 = t0erm_cbv_evaluate0(term.arg2)
        if isinstance(t1, T0Mlam):
            return t0erm_cbv_evaluate0(t0erm_subst0(t1.arg2, t1.arg1, t2))
        elif isinstance(t1, T0Mfix):
            # Substitute the argument, then bind the recursive name to t1.
            return t0erm_cbv_evaluate0\
                (t0erm_subst0(t0erm_subst0(t1.arg3, t1.arg2, t2), t1.arg1, t1))
        else:
            raise TypeError(f"t0erm_cbv_evaluate0: application expects a lam/fix ({t1})")
    elif isinstance(term, T0Mif0):
        t1 = t0erm_cbv_evaluate0(term.arg1)
        if isinstance(t1, T0Mbtf):
            if t1.arg1:
                return t0erm_cbv_evaluate0(term.arg2)
            else:
                return t0erm_cbv_evaluate0(term.arg3)
        else:
            raise TypeError(f"t0erm_cbv_evaluate0: condition expects a boolean ({t1})")
    elif isinstance(term, T0Mop1):
        if term.arg1 in ("+", "-"):
            t1 = t0erm_cbv_evaluate0(term.arg2)
            if isinstance(t1, T0Mint):
                if term.arg1 == "+":
                    return T0Mint(t1.arg1)
                else:
                    return T0Mint(-(t1.arg1))
            else:
                raise TypeError(f"t0erm_cbv_evaluate0: {term.arg1} expects integers ({t1})")
        else:
            raise TypeError(f"t0erm_cbv_evaluate0({term})")
    elif isinstance(term, T0Mop2):
        if term.arg1 in ("+", "-", "*", "/", "%"):
            t1 = t0erm_cbv_evaluate0(term.arg2)
            t2 = t0erm_cbv_evaluate0(term.arg3)
            if isinstance(t1, T0Mint) and isinstance(t2, T0Mint):
                if term.arg1 == "+":
                    return T0Mint(t1.arg1 + t2.arg1)
                elif term.arg1 == "-":
                    return T0Mint(t1.arg1 - t2.arg1)
                elif term.arg1 == "*":
                    return T0Mint(t1.arg1 * t2.arg1)
                elif term.arg1 == "%":
                    return T0Mint(t1.arg1 % t2.arg1)
                else: # term.arg1 == "/"
                    # Integer division rounds down, as in Python.
                    return T0Mint(t1.arg1 // t2.arg1)
            else:
                raise TypeError(f"t0erm_cbv_evaluate0: {term.arg1} expects integers ({t1}, {t2})")
        elif term.arg1 in ("<", ">", "<=", ">=", "==", "!="):
            t1 = t0erm_cbv_evaluate0(term.arg2)
            t2 = t0erm_cbv_evaluate0(term.arg3)
            if isinstance(t1, T0Mint) and isinstance(t2, T0Mint):
                if term.arg1 == "<":
                    return T0Mbtf(t1.arg1 < t2.arg1)
                elif term.arg1 == ">":
                    return T0Mbtf(t1.arg1 > t2.arg1)
                elif term.arg1 == "<=":
                    return T0Mbtf(t1.arg1 <= t2.arg1)
                elif term.arg1 == ">=":
                    return T0Mbtf(t1.arg1 >= t2.arg1)
                elif term.arg1 == "==":
                    return T0Mbtf(t1.arg1 == t2.arg1)
                else: # term.arg1 == "!="
                    return T0Mbtf(t1.arg1 != t2.arg1)
            else:
                raise TypeError(f"t0erm_cbv_evaluate0: {term.arg1} expects integers ({t1}, {t2})")
        else:
            raise TypeError(f"t0erm_cbv_evaluate0({term})")
    else:
        raise TypeError(f"t0erm_cbv_evaluate0({term})")        
#
########################################################################
########################################################################
# end of [CS413-2026-Fall/assigns/02/lambda0.py]
########################################################################
########################################################################
