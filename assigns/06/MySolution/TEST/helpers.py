"""Shared test setup: path to MySolution and small helpers."""
from __future__ import annotations

import sys
from pathlib import Path

SOLUTION = Path(__file__).resolve().parent.parent
if str(SOLUTION) not in sys.path:
    sys.path.insert(0, str(SOLUTION))

from evaluator import evaluate            # noqa: E402
from observe import BOOL, NAT, observe    # noqa: E402
from pipeline import run_program, source_result  # noqa: E402

EXEC = 20_000        # execution budget used by the tests
OBS = 20_000         # observation budget used by the tests
SHORT = 3_000        # budget for programs expected to diverge


def decode(term, kind, exec_budget=EXEC, obs_budget=OBS):
    """Evaluate a closed target term and observe it; fail loudly otherwise."""
    result = evaluate(term, exec_budget)
    if not result.completed:
        raise AssertionError(f"execution exhausted after {result.steps} steps")
    obs = observe(result.value, kind, obs_budget)
    if not obs.ok:
        raise AssertionError(f"observation {obs.status}: {obs.detail}")
    return obs.value


def nat(term):
    return decode(term, NAT)


def boolean(term):
    return decode(term, BOOL)


def compiled_answer(source, kind):
    """Compile, execute and observe a source program; return the decoded value."""
    report = run_program(source, kind, EXEC, OBS)
    if not report.execution.completed:
        raise AssertionError("execution exhausted")
    if not report.observation.ok:
        raise AssertionError(f"observation {report.observation.status}")
    return report.decoded


def compiled_exhausts(source, budget=SHORT) -> bool:
    report = run_program(source, NAT, budget, OBS)
    return (not report.execution.completed) and report.execution.steps == budget


__all__ = ["EXEC", "OBS", "SHORT", "decode", "nat", "boolean",
           "compiled_answer", "compiled_exhausts", "source_result", "NAT", "BOOL"]
