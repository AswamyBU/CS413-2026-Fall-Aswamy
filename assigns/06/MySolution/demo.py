"""Command-line demonstration: compile, execute, and observe every example.

Run from assigns/06:

    python MySolution/demo.py
    python MySolution/demo.py --exec-budget 5000 --obs-budget 2000 --only DEMO-10

For each example this prints the source program, the generated pure term
(inline when short; every term is also saved under MySolution/generated/),
the result of the shared evaluator on the source AST, the execution outcome
and beta-value step count, the observation outcome and its separate step
count, the decoded answer, and the explicit expected answer.

Exit status is 0 when every example matches its expected answer, else 1.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from examples import EXAMPLES, Example          # noqa: E402
from observe import kind_name                    # noqa: E402
from pipeline import run_program, source_result  # noqa: E402
from source_syntax import pretty                 # noqa: E402
from target import is_pure, show, term_size      # noqa: E402

DEFAULT_EXEC_BUDGET = 10_000
DEFAULT_OBS_BUDGET = 10_000
INLINE_LIMIT = 400        # print generated terms up to this many characters


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple):
        return "(" + ", ".join(_fmt(v) for v in value) + ")"
    return str(value)


def run_example(ex: Example, exec_budget: int, obs_budget: int,
                out_dir: Path | None) -> bool:
    report = run_program(ex.source, ex.kind, exec_budget, obs_budget)
    text = show(report.term)
    print(f"{ex.ident}  {ex.notation}")
    print(f"  source       : {pretty(ex.source)}")
    saved = ""
    if out_dir is not None:
        path = out_dir / f"{ex.ident}.txt"
        path.write_text(text + "\n", encoding="utf-8")
        saved = f"saved to {path.relative_to(HERE.parent).as_posix()}"
    pure = "pure" if is_pure(report.term) else "NOT PURE"
    if len(text) <= INLINE_LIMIT:
        print(f"  pure term    : {text}")
        print(f"                 ({term_size(report.term)} nodes, {pure}; {saved})")
    else:
        print(f"  pure term    : {len(text)} characters, {term_size(report.term)} nodes, "
              f"{pure}; {saved}")
        print(f"                 {text[:110]}...")

    if ex.diverges:
        print("  source eval  : skipped (program diverges)")
    else:
        print(f"  source eval  : {_fmt(source_result(ex.source))}")

    ex_res = report.execution
    if ex_res.completed:
        print(f"  execution    : value after {ex_res.steps} beta-value steps "
              f"(budget {exec_budget})")
    else:
        print(f"  execution    : budget exhausted after {ex_res.steps} beta-value "
              f"steps (budget {exec_budget}); this is not a proof of nontermination")

    obs = report.observation
    if obs is None:
        print("  observation  : not run (execution did not reach a value)")
        decoded = "none"
    else:
        tail = f" -- {obs.detail}" if obs.detail else ""
        print(f"  observation  : {obs.status} as {kind_name(ex.kind)} after "
              f"{obs.steps} beta-value steps (budget {obs_budget}){tail}")
        decoded = _fmt(obs.value) if obs.ok else "none"

    if ex.diverges:
        passed = not ex_res.completed
        expected = "execution budget exhaustion"
    else:
        passed = report.decoded == ex.expected and type(report.decoded) is type(ex.expected)
        expected = _fmt(ex.expected)
    print(f"  decoded      : {decoded}")
    print(f"  expected     : {expected}")
    print(f"  result       : {'PASS' if passed else 'FAIL'}")
    print()
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--exec-budget", type=int, default=DEFAULT_EXEC_BUDGET,
                        help="max beta-value steps for executing a compiled program "
                             f"(default {DEFAULT_EXEC_BUDGET})")
    parser.add_argument("--obs-budget", type=int, default=DEFAULT_OBS_BUDGET,
                        help="max beta-value steps for observing/decoding a result "
                             f"(default {DEFAULT_OBS_BUDGET})")
    parser.add_argument("--only", nargs="*", metavar="ID",
                        help="run only these example ids, e.g. DEMO-10 EXTRA-1")
    parser.add_argument("--mandatory", action="store_true",
                        help="run only the fourteen required demonstrations")
    parser.add_argument("--no-save", action="store_true",
                        help="do not write generated terms to MySolution/generated/")
    args = parser.parse_args(argv)
    if args.exec_budget < 0 or args.obs_budget < 0:
        parser.error("budgets must be nonnegative")

    examples = [e for e in EXAMPLES
                if (not args.only or e.ident in args.only)
                and (not args.mandatory or e.mandatory)]
    out_dir = None
    if not args.no_save:
        out_dir = HERE / "generated"
        out_dir.mkdir(exist_ok=True)

    print(f"Execution budget: {args.exec_budget} beta-value steps; "
          f"observation budget: {args.obs_budget} beta-value steps.\n")
    results = [run_example(e, args.exec_budget, args.obs_budget, out_dir)
               for e in examples]
    print(f"{sum(results)}/{len(results)} examples matched their expected answers.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
