"""Non-intelligent execution of a previously frozen plan."""

from __future__ import annotations

from typing import Any

from ..benchmark.base import ExperimentOracle, Observation


def execute_frozen_plan(oracle: ExperimentOracle, plan: list[dict[str, Any]]) -> list[Observation]:
    """Execute exactly the supplied sequence; no result can affect later actions."""

    frozen = tuple(plan)
    return [oracle.run_experiment(action) for action in frozen]
