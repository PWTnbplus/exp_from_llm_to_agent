"""Public benchmark contracts.

The objects in this module deliberately contain no ground-truth law, evaluator
state, or validation data.  They are the only benchmark metadata exposed to a
model runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class TaskSpec:
    """A reproducible task identifier and public metadata."""

    task_id: str
    source: str
    module: str
    domain: str
    law_complexity: str
    system_complexity: str
    law_variant: str
    split: str = "test"
    seed: int = 42
    supported: bool = True
    notes: str = ""


@dataclass(frozen=True)
class Observation:
    """One oracle response, with no hidden fields."""

    experiment_index: int
    action: dict[str, Any]
    result: Any
    measurement_count: int


class ExperimentOracle(Protocol):
    """Minimal discovery-environment contract."""

    def get_public_task_description(self) -> str: ...

    def get_initial_observations(self) -> list[Observation]: ...

    def get_action_schema(self) -> dict[str, Any]: ...

    def run_experiment(self, action: dict[str, Any]) -> Observation: ...

    def get_remaining_budget(self) -> dict[str, int | float]: ...

    def finalize(self) -> None: ...


@dataclass
class RunResult:
    """Serializable output shared by both runners."""

    runner: str
    task_id: str
    status: str
    law: dict[str, Any]
    observations: list[Observation] = field(default_factory=list)
    plan: list[dict[str, Any]] = field(default_factory=list)
    plan_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

