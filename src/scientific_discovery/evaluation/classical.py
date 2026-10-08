"""Extension point for non-LLM scientific baselines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..benchmark.base import TaskSpec


class ClassicalBaseline(ABC):
    """A future system-identification baseline with the same oracle boundary."""

    name = "classical_baseline"

    @abstractmethod
    def fit(self, task: TaskSpec, observations: list[dict[str, Any]]) -> dict[str, Any]:
        """Fit only from observations explicitly authorized by the protocol."""
        raise NotImplementedError
