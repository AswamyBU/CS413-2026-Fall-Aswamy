"""Compile -> execute -> observe, in one call.

    run_program(source, kind, exec_budget, obs_budget) -> RunReport
    source_result(source) -> Python data from the shared evaluator

Execution and observation have separate budgets and separate step counts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from compiler import compile_expr
from evaluator import EvalResult, evaluate
from observe import Observation, observe
from source_syntax import d0exp, source_value_to_python
from target import Term

__all__ = ["RunReport", "run_program", "source_result"]


@dataclass(frozen=True)
class RunReport:
    term: Term                         # the generated pure term
    execution: EvalResult              # status, value, steps, budget
    observation: Observation | None    # None if execution did not finish
    obs_budget: int | None

    @property
    def decoded(self) -> Any:
        if self.observation is not None and self.observation.ok:
            return self.observation.value
        return None


def run_program(source: d0exp, kind, exec_budget: int | None,
                obs_budget: int | None) -> RunReport:
    term = compile_expr(source)
    execution = evaluate(term, exec_budget)
    observation = (observe(execution.value, kind, obs_budget)
                   if execution.completed else None)
    return RunReport(term, execution, observation, obs_budget)


def source_result(source: d0exp, budget: int | None = None) -> Any:
    """Evaluate a source AST with the shared evaluator and return Python data
    (int, bool, tuple, or "<function>"). Returns None if ``budget`` ran out."""
    result = evaluate(source, budget)
    return source_value_to_python(result.value) if result.completed else None
