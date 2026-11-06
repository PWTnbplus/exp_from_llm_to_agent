"""Independent evaluator environment; model runners never receive its data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .law_recovery import LawCandidate, NewtonBenchLawEvaluator
from ..benchmark.base import TaskSpec


class ValidationEnvironment:
    def __init__(self, repo_root: Path):
        self.evaluator = NewtonBenchLawEvaluator(repo_root)

    def validate(self, task: TaskSpec, law: dict[str, Any]) -> dict[str, Any]:
        if "error" in law:
            return {"validated_success": False, "numeric_fit": False, "structural_recovery": None, "mechanistic_validity": "not_implemented", "error": law["error"], "validation_queries_before_submission": 0}
        candidate = LawCandidate(**law)
        result = self.evaluator.evaluate(task, candidate)
        result["validation_queries_before_submission"] = 0
        return result
