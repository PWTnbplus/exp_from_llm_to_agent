"""Independent evaluator environment; model runners never receive its data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .law_recovery import LawCandidate, NewtonBenchLawEvaluator
from .scoring import SCORING_PROTOCOL
from ..benchmark.base import TaskSpec


class ValidationEnvironment:
    def __init__(self, repo_root: Path):
        self.evaluator = NewtonBenchLawEvaluator(repo_root)

    def validate(self, task: TaskSpec, law: dict[str, Any]) -> dict[str, Any]:
        if "error" in law:
            return {
                "validated_success": False,
                "numeric_fit": False,
                "ood_fit": False,
                "structural_recovery": False,
                "mechanistic_validity": False,
                "equivalence_class": "none",
                "error": law["error"],
                "success_definition": "numeric_fit_and_structural_recovery_and_ood",
                "scoring_protocol_version": SCORING_PROTOCOL["version"],
                "validation_queries_before_submission": 0,
            }
        candidate = LawCandidate(**law)
        result = self.evaluator.evaluate(task, candidate)
        result["validation_queries_before_submission"] = 0
        return result
