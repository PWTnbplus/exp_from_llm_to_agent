"""Thin adapter around the pinned NewtonBench simulator.

Only this adapter imports upstream law implementations.  The public methods
return task descriptions, schemas and measurements; hidden law functions and
the upstream evaluator never cross the runner boundary.
"""

from __future__ import annotations

import importlib
import inspect
import math
import re
from pathlib import Path
from typing import Any

from .base import Observation, TaskSpec
from ..environment.budget import BudgetExceeded, BudgetLedger
from ..environment.isolation import json_safe_copy
from ..utils.json_protocol import parse_json_object


class ActionValidationError(ValueError):
    pass


def _function_parameters(module: Any) -> list[str]:
    signature = getattr(module, "FUNCTION_SIGNATURE", "")
    match = re.search(r"discovered_law\((.*?)\)", signature)
    if match:
        return [part.strip() for part in match.group(1).split(",") if part.strip()]
    fn = getattr(module, "run_experiment_for_module", None)
    if fn:
        return [
            p.name for p in inspect.signature(fn).parameters.values()
            if p.name not in {"noise_level", "difficulty", "system", "law_version"}
            and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
            and p.default is inspect.Parameter.empty
        ]
    return []


def _measurement_count(result: Any) -> int:
    if isinstance(result, dict):
        values = [v for v in result.values() if isinstance(v, list)]
        return max((len(v) for v in values), default=1)
    if isinstance(result, list):
        return len(result)
    return 1


class NewtonBenchOracle:
    """Discovery-only wrapper for one fixed NewtonBench task."""

    def __init__(self, task: TaskSpec, repo_root: Path, budget: BudgetLedger, noise_level: float = 0.0):
        self.task = task
        self.repo_root = Path(repo_root).resolve()
        self.budget = budget
        self.noise_level = float(noise_level)
        self._module = None
        self._observations: list[Observation] = []
        self._closed = False
        self._reset()

    def _reset(self) -> None:
        if str(self.repo_root) not in __import__("sys").path:
            __import__("sys").path.insert(0, str(self.repo_root))
        self._module = importlib.import_module(f"modules.{self.task.module}")
        self._observations = []
        self._closed = False

    def get_public_task_description(self) -> str:
        params = getattr(self._module, "PARAM_DESCRIPTION", "Each control is a finite real number.")
        return (
            "You are studying an unknown law in a controlled scientific system.\n"
            "The target law and its parameters are hidden from the model.\n"
            f"Scientific domain: {self.task.domain}.\n"
            "You may choose only the controls in the action schema. The oracle returns "
            "a measurement, and no source code or evaluation data is available.\n"
            f"Controls:\n{params}"
        )

    def get_initial_observations(self) -> list[Observation]:
        return []

    def get_action_schema(self) -> dict[str, Any]:
        params = _function_parameters(self._module)
        properties = {
            name: {"type": "number", "description": "finite numeric experimental control"}
            for name in params
        }
        return {
            "type": "object",
            "properties": properties,
            "required": params,
            "additionalProperties": False,
        }

    def _validate_action(self, action: dict[str, Any]) -> dict[str, float]:
        if not isinstance(action, dict):
            raise ActionValidationError("action must be an object")
        required = set(self.get_action_schema()["required"])
        if set(action) != required:
            raise ActionValidationError(f"action keys must be exactly {sorted(required)}")
        clean: dict[str, float] = {}
        for key, value in action.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ActionValidationError(f"{key} must be numeric")
            value = float(value)
            if not math.isfinite(value):
                raise ActionValidationError(f"{key} must be finite")
            if key in {"mass1", "mass2", "distance", "q1", "q2", "current1", "current2", "k", "m", "b", "N0", "lambda_constant", "T", "M", "gamma", "I_0", "A", "d", "c"} and value <= 0:
                raise ActionValidationError(f"{key} must be positive")
            clean[key] = value
        return clean

    def run_experiment(self, action: dict[str, Any]) -> Observation:
        if self._closed:
            raise RuntimeError("oracle has been finalized")
        clean = self._validate_action(action)
        self.budget.consume_experiment(measurement_count=1)
        result = self._module.run_experiment_for_module(
            **clean,
            noise_level=self.noise_level,
            difficulty=self.task.law_complexity,
            system=self.task.system_complexity,
            law_version=self.task.law_variant,
        )
        result = json_safe_copy(result)
        obs = Observation(
            experiment_index=len(self._observations),
            action=clean,
            result=result,
            measurement_count=_measurement_count(result),
        )
        self._observations.append(obs)
        self.budget.add_measurements(obs.measurement_count - 1)
        return obs

    def get_remaining_budget(self) -> dict[str, int | float]:
        return self.budget.remaining()

    def finalize(self) -> None:
        self._closed = True


def parse_task_id(task_id: str) -> tuple[str, str, str, str]:
    prefix, module, difficulty, variant, system = task_id.split(":", 4)
    if prefix != "newtonbench":
        raise ValueError(f"unsupported task source: {prefix}")
    return module, difficulty, variant, system
