import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXAMPLES = ROOT / "examples"


def example(name: str) -> str:
    return (EXAMPLES / f"{name}.lambda").read_text(encoding="utf-8")


def factorial_src(n: int) -> str:
    return f'''
D0Eapp(D0Efix("fact", "n",
    D0Eif0(D0Eop2("<=", D0Evar("n"), D0Eint(0)), D0Eint(1),
           D0Eop2("*", D0Evar("n"),
                  D0Eapp(D0Evar("fact"), D0Eop2("-", D0Evar("n"), D0Eint(1)))))),
  D0Eint({n}))'''


def fibonacci_src(n: int) -> str:
    return f'''
D0Eapp(D0Efix("fib", "n",
    D0Eif0(D0Eop2("<", D0Evar("n"), D0Eint(2)), D0Evar("n"),
           D0Eop2("+", D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(1))),
                       D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(2)))))),
  D0Eint({n}))'''
