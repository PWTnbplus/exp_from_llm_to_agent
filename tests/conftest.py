from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scientific_discovery.benchmark.base import Observation
from scientific_discovery.environment.budget import BudgetLedger


@dataclass
class FakeOracle:
    values: list[float]
    budget: BudgetLedger

    def __post_init__(self):
        self.i = 0
        self.actions: list[dict[str, Any]] = []
        self.closed = False

    def get_public_task_description(self) -> str:
        return "You are studying an unknown law. Scientific domain: test. Controls: x is a finite number."

    def get_initial_observations(self):
        return []

    def get_action_schema(self):
        return {"type": "object", "properties": {"x": {"type": "number"}}, "required": ["x"], "additionalProperties": False}

    def run_experiment(self, action):
        self.budget.consume_experiment()
        self.actions.append(action)
        obs = Observation(self.i, action, self.values[self.i % len(self.values)], 1)
        self.i += 1
        return obs

    def get_remaining_budget(self):
        return self.budget.remaining()

    def finalize(self):
        self.closed = True
