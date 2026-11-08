########################################################################
# Requires Python 3.12 or later.
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
########################################################################

#
@dataclass
class fnoptn[T](ABC):
    pass
@dataclass
class fnoptn_nil[T](fnoptn[T]):
    pass
@dataclass
class fnoptn_cons[T](fnoptn[T]):
    arg1: T
    pass
#
########################################################################
#
@dataclass
class fnlist[T](ABC):
    pass
@dataclass
class fnlist_nil[T](fnlist[T]):
    pass
@dataclass
class fnlist_cons[T](fnlist[T]):
    arg1: T
    arg2: fnlist[T]
    pass
#
########################################################################

def fnlist_reverse[T](items: fnlist[T]) -> fnlist[T]:
    result = fnlist_nil()
    while isinstance(items, fnlist_cons):
        result = fnlist_cons(items.arg1, result)
        items = items.arg2
    return result

########################################################################

def fnlist_map[T, U](items: fnlist[T], f: Callable[[T], U]) -> fnlist[U]:
    """Apply f to each element in order, returning a new list."""
    result: fnlist[U] = fnlist_nil()
    while isinstance(items, fnlist_cons):
        result = fnlist_cons(f(items.arg1), result)
        items = items.arg2
    return fnlist_reverse(result)

########################################################################

def fnlist_foldleft[T, U](
    items: fnlist[T], initial: U, f: Callable[[U, T], U]
) -> U:
    """Combine elements from left to right using f(accumulator, element)."""
    result = initial
    while isinstance(items, fnlist_cons):
        result = f(result, items.arg1)
        items = items.arg2
    return result

########################################################################

def fnlist_foldright[T, U](
    items: fnlist[T], initial: U, f: Callable[[T, U], U]
) -> U:
    """Combine elements from right to left using f(element, accumulator)."""
    result = initial
    items = fnlist_reverse(items)
    while isinstance(items, fnlist_cons):
        result = f(items.arg1, result)
        items = items.arg2
    return result

########################################################################
