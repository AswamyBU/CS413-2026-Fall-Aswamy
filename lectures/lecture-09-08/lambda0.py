########################################################################
########################################################################
# playing with lambda calculus
########################################################################
########################################################################
type nint = int
type sint = int
type strn = str
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
    arg1: strn
    ctag = "T0Mvar"
########################################################################
@dataclass
class T0Mlam(T0M000):
    arg1: strn
    arg2: t0erm
    ctag = "T0Mlam"
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
########################################################################
@dataclass
class T0Mif0(T0M000):
    arg1: t0erm
    arg2: t0erm
    arg3: t0erm
    ctag = "T0Mif0"
########################################################################
EX_I = T0Mlam("x", T0Mvar("x"))
print(f"EX_I = {EX_I}")
########################################################################
EX_K = T0Mlam("x", T0Mlam("y", T0Mvar("x")))
print(f"EX_K = {EX_K}")
########################################################################
EX_S = T0Mlam("x", T0Mlam("y", T0Mlam("z", T0Mapp(T0Mapp(T0Mvar("x"), T0Mvar("z")), T0Mapp(T0Mvar("y"), T0Mvar("z"))))))
print(f"EX_S = {EX_S}")
########################################################################
def t0erm_size(term: t0erm) -> sint:
    if False:
        return 0
    elif isinstance(term, T0Mint):
        return 1
    elif isinstance(term, T0Mbtf):
        return 1
    elif isinstance(term, T0Mvar):
        return 1
    elif isinstance(term, T0Mlam):
        return 1 + t0erm_size(term.arg2)
    elif isinstance(term, T0Mapp):
        return 1 + t0erm_size(term.arg1) + t0erm_size(term.arg2)
    elif isinstance(term, T0Mif0):
        return 1 + t0erm_size(term.arg1) + t0erm_size(term.arg2) + t0erm_size(term.arg3)
    else:
        raise TypeError(f"t0erm_size({term})")
########################################################################
print(f"size(EX_I) = {t0erm_size(EX_I)}")
print(f"size(EX_K) = {t0erm_size(EX_K)}")
print(f"size(EX_S) = {t0erm_size(EX_S)}")
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
    elif isinstance(term, T0Mvar):
        return frozenset([term.arg1])
    elif isinstance(term, T0Mlam):
        return t0erm_fvset(term.arg2) - {term.arg1}
    elif isinstance(term, T0Mapp):
        return (t0erm_fvset(term.arg1) | t0erm_fvset(term.arg2))
    elif isinstance(term, T0Mif0):
        return (t0erm_fvset(term.arg1) | t0erm_fvset(term.arg2) | t0erm_fvset(term.arg3))
    else:
        raise TypeError(f"t0erm_fvset({term})")
########################################################################
print(f"fvset(EX_I) = {t0erm_fvset(EX_I)}")
print(f"fvset(EX_K) = {t0erm_fvset(EX_K)}")
print(f"fvset(EX_S) = {t0erm_fvset(EX_S)}")        
########################################################################
#
type tvar = strn
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
        elif isinstance(term, T0Mvar):
            return tsub if x0 == term.arg1 else term
        elif isinstance(term, T0Mlam):
            x1 = term.arg1
            if x0 == x1:
                return term
            else:
                return T0Mlam(x1, subst0(term.arg2))
        elif isinstance(term, T0Mapp):
            return T0Mapp(subst0(term.arg1), subst0(term.arg2))
        elif isinstance(term, T0Mif0):
            return T0Mif0(subst0(term.arg1), subst0(term.arg2), subst0(term.arg3))
        else:
            raise TypeError(f"subst0({term})")
    return subst0(term)
#
########################################################################
########################################################################
