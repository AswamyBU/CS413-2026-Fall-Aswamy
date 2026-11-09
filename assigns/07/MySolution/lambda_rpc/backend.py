"""Locate and import the provided LAMBDA3 implementation.

This is the only module that knows where LAMBDA3 lives. Everything else uses
`backend.L` (the lambda3 module) and `backend.build`.
"""

import os
import sys
from functools import cache
from pathlib import Path

LAMBDA3_DIR = Path(
    os.environ.get("LAMBDA3_DIR")
    or Path(__file__).resolve().parents[2] / "LAMBDA3"
)
if str(LAMBDA3_DIR) not in sys.path:
    # lambda3.py does `from basics0 import ...`, so its folder must be on the path.
    sys.path.insert(0, str(LAMBDA3_DIR))

import lambda3 as L  # noqa: E402  (provided implementation, used unchanged)

# Standard libraries from LAMBDA3/mylib/, in the order they are bound.
LIBRARY_NAMES = ("list", "optn", "a1sz", "strm")


@cache
def load_library(name: str):
    """Parse one mylib/<name>.lam file into LAMBDA3 declarations (cached)."""
    if name not in LIBRARY_NAMES:
        raise ValueError(f"unknown library {name!r}")
    text = (LAMBDA3_DIR / "mylib" / f"{name}.lam").read_text(encoding="utf-8")
    return L.d0cls_parse(text)


def build(source: str, libraries: tuple[str, ...] = ()):
    """Parse and type-check `source`; return (expression, type).

    Raises L.LambdaSyntaxError or L.TypeCheckError. With no libraries this is
    exactly `d0exp_parse_and_typecheck`. With libraries, the user's source is
    parsed on its own (so syntax-error positions refer to the user's text),
    wrapped in the library declarations the same way mylib/TEST does
    (`D0Elets(declarations, expression)`), and the whole thing type-checked.
    """
    if not libraries:
        return L.d0exp_parse_and_typecheck(source)
    expression = L.d0exp_parse(source)
    ordered = [name for name in LIBRARY_NAMES if name in libraries]
    for name in reversed(ordered):
        expression = L.D0Elets(load_library(name), expression)
    return expression, L.d0exp_typecheck(expression)
