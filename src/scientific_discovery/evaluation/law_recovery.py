"""Common law schema and objective numeric evaluation."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
import importlib
import inspect
import math
from pathlib import Path
import random
from typing import Any, Callable

import numpy as np

from ..benchmark.base import TaskSpec
from ..benchmark.newtonbench_adapter import public_action_rules
from ..benchmark.task_registry import ensure_upstream_importable
from ..utils.json_protocol import ProtocolError, parse_json_object
from .scoring import SCORING_PROTOCOL, structurally_equivalent


@dataclass
class LawCandidate:
    task_id: str
    hypothesis: str
    equation: str
    variables: list[str]
    parameters: dict[str, float]
    evidence: list[str] = field(default_factory=list)
    predictions: list[Any] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    code: str = ""

    @classmethod
    def from_payload(cls, payload: str | dict[str, Any], task_id: str) -> "LawCandidate":
        data = parse_json_object(payload)
        if "final_law" in data:
            data = data["final_law"]
        if not isinstance(data, dict):
            raise ProtocolError("final_law must be an object")
        required = ("hypothesis", "equation", "variables", "parameters")
        missing = [key for key in required if key not in data]
        if missing:
            raise ProtocolError(f"final law missing fields: {missing}")
        if not isinstance(data["variables"], list) or not isinstance(data["parameters"], dict):
            raise ProtocolError("variables must be a list and parameters must be an object")
        params: dict[str, float] = {}
        for key, value in data["parameters"].items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ProtocolError(f"parameter {key} must be finite numeric")
            params[str(key)] = float(value)
        code = data.get("code", "")
        if code is not None and not isinstance(code, str):
            raise ProtocolError("code must be a string when present")
        return cls(
            task_id=task_id,
            hypothesis=str(data["hypothesis"]),
            equation=str(data["equation"]),
            variables=[str(v) for v in data["variables"]],
            parameters=params,
            evidence=[str(v) for v in data.get("evidence", [])],
            predictions=list(data.get("predictions", [])),
            limitations=[str(v) for v in data.get("limitations", [])],
            code=code or "",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_function(source: str, expected_parameters: list[str]) -> Callable[..., float]:
    if not source:
        raise ValueError("candidate has no executable law code")
    tree = ast.parse(source, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.With, ast.Try, ast.Lambda)):
            raise ValueError("candidate code contains a forbidden construct")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "open", "compile", "__import__"}:
            raise ValueError("candidate code contains a forbidden call")
    namespace = {
        "__builtins__": {"abs": abs, "float": float, "max": max, "min": min, "pow": pow, "sum": sum},
        "math": math,
    }
    local: dict[str, Any] = {}
    exec(compile(tree, "<candidate-law>", "exec"), namespace, local)
    fn = local.get("discovered_law")
    if not callable(fn):
        raise ValueError("candidate code must define discovered_law")
    actual = list(__import__("inspect").signature(fn).parameters)
    if actual != expected_parameters:
        raise ValueError(f"candidate signature {actual} does not match {expected_parameters}")
    return fn


def _task_module(task: TaskSpec, repo_root: Path) -> tuple[Any, Callable[..., float], list[str]]:
    ensure_upstream_importable(repo_root)
    module = importlib.import_module(f"modules.{task.module}")
    laws = importlib.import_module(f"modules.{task.module}.laws")
    gt_law, _ = laws.get_ground_truth_law(task.law_complexity, task.law_variant)
    signature = getattr(module, "FUNCTION_SIGNATURE", "")
    inside = signature.partition("(")[2].partition(")")[0]
    parameters = [v.strip() for v in inside.split(",") if v.strip()]
    return module, gt_law, parameters


class NewtonBenchLawEvaluator:
    """Evaluate numerical, structural and mechanistic law recovery.

    All target-law access and OOD interventions remain inside this evaluator;
    callers receive only aggregate scores after the candidate is submitted.
    """

    def __init__(
        self,
        repo_root: Path,
        test_points: int = int(SCORING_PROTOCOL["validation_points"]),
        relative_tolerance: float = float(SCORING_PROTOCOL["relative_rmse_threshold"]),
        ood_points: int = int(SCORING_PROTOCOL["ood_points"]),
        ood_relative_tolerance: float = float(SCORING_PROTOCOL["ood_relative_rmse_threshold"]),
    ):
        self.repo_root = Path(repo_root)
        self.test_points = int(test_points)
        self.relative_tolerance = float(relative_tolerance)
        self.ood_points = int(ood_points)
        self.ood_relative_tolerance = float(ood_relative_tolerance)

    def _actions(self, task: TaskSpec, *, split: str) -> list[dict[str, float]]:
        if split == "ood":
            return self._ood_actions(task)
        rng = random.Random(task.seed * 1009 + 17)
        _, _, params = _task_module(task, self.repo_root)
        rules = public_action_rules(task.module)
        actions = []
        for _ in range(self.test_points):
            values: dict[str, float] = {}
            for name in params:
                rule = rules.get(name, {})
                minimum = rule.get("minimum")
                maximum = rule.get("maximum")
                if minimum is not None and maximum is not None:
                    values[name] = rng.uniform(float(minimum), float(maximum))
                elif minimum is not None and float(minimum) >= 0:
                    # The public metadata only gives a lower bound for these
                    # controls.  Keep the existing broad log-scale coverage,
                    # shifted above a strictly positive lower bound.
                    low = float(minimum)
                    if rule.get("exclusiveMinimum"):
                        low = max(low, 1e-6)
                    values[name] = low + 10 ** rng.uniform(-0.3, 1.5)
                else:
                    values[name] = 10 ** rng.uniform(-0.3, 1.5)
            actions.append(values)
        return actions

    def _ood_actions(self, task: TaskSpec) -> list[dict[str, float]]:
        """Build deterministic distribution-shifted legal interventions.

        OOD here means held-out interventions at apparatus boundaries and
        extrapolative positive scales, not illegal controls.  This prevents a
        claim of mechanistic validity from resting only on the validation
        sampling distribution.
        """

        _, _, params = _task_module(task, self.repo_root)
        rules = public_action_rules(task.module)
        actions: list[dict[str, float]] = []
        for index in range(self.ood_points):
            action: dict[str, float] = {}
            for offset, name in enumerate(params):
                rule = rules.get(name, {})
                level = index + offset
                minimum = rule.get("minimum")
                maximum = rule.get("maximum")
                if minimum is not None and maximum is not None:
                    low = float(minimum)
                    high = float(maximum)
                    span = high - low
                    epsilon = max(span * 1e-6, 1e-8)
                    lower = low + epsilon if rule.get("exclusiveMinimum") else low
                    levels = (lower, low + 0.1 * span, low + 0.5 * span, high - 0.1 * span, high)
                    action[name] = float(levels[level % len(levels)])
                else:
                    low = float(minimum) if minimum is not None else 0.0
                    lower = max(low + (1e-6 if rule.get("exclusiveMinimum") else 0.0), 1e-6)
                    levels = (lower, lower * 1.01, lower + 0.01, lower + 1.0, lower + 1000.0)
                    action[name] = float(levels[level % len(levels)])
            actions.append(action)
        return actions

    @staticmethod
    def _score_actions(fn: Callable[..., float], gt_law: Callable[..., float], actions: list[dict[str, float]]) -> dict[str, Any]:
        valid_actions: list[dict[str, float]] = []
        y_true: list[float] = []
        for action in actions:
            try:
                value = float(gt_law(**action))
            except Exception:
                continue
            if math.isfinite(value):
                valid_actions.append(action)
                y_true.append(value)

        if not valid_actions:
            return {"relative_rmse": float("nan"), "rmsle": float("nan"), "n_points": 0, "all_predictions_finite": False}

        predictions: list[float] = []
        for action in valid_actions:
            try:
                predictions.append(float(fn(**action)))
            except Exception:
                predictions.append(float("nan"))
        y_true_array = np.asarray(y_true, dtype=float)
        y_pred_array = np.asarray(predictions, dtype=float)
        finite = bool(np.all(np.isfinite(y_pred_array)))
        if not finite:
            return {
                "relative_rmse": float("inf"),
                "rmsle": float("inf"),
                "n_points": len(valid_actions),
                "all_predictions_finite": False,
            }
        relative_rmse = float(np.sqrt(np.mean(((y_pred_array - y_true_array) / np.maximum(np.abs(y_true_array), 1e-12)) ** 2)))
        rmsle = float(np.sqrt(np.mean((np.log1p(np.maximum(y_pred_array, 0)) - np.log1p(np.maximum(y_true_array, 0))) ** 2)))
        return {
            "relative_rmse": relative_rmse,
            "rmsle": rmsle,
            "n_points": len(valid_actions),
            "all_predictions_finite": True,
        }

    @staticmethod
    def _failure(error: str, *, upstream_ground_truth_function_used: bool = False) -> dict[str, Any]:
        return {
            "validated_success": False,
            "numeric_fit": False,
            "ood_fit": False,
            "structural_recovery": False,
            "mechanistic_validity": False,
            "equivalence_class": "none",
            "rmsle": float("nan"),
            "relative_rmse": float("nan"),
            "ood_rmsle": float("nan"),
            "ood_relative_rmse": float("nan"),
            "n_validation_points": 0,
            "n_ood_points": 0,
            "error": error,
            "official_numeric_evaluator": False,
            "upstream_ground_truth_function_used": upstream_ground_truth_function_used,
            "success_definition": "numeric_fit_and_structural_recovery_and_ood",
            "symbolic_judge_used": False,
            "scoring_protocol_version": SCORING_PROTOCOL["version"],
        }

    def evaluate(self, task: TaskSpec, candidate: LawCandidate) -> dict[str, Any]:
        try:
            module, gt_law, params = _task_module(task, self.repo_root)
            fn = _safe_function(candidate.code, params)
        except Exception as exc:
            return self._failure(str(exc))

        try:
            validation_score = self._score_actions(fn, gt_law, self._actions(task, split="validation"))
            ood_score = self._score_actions(fn, gt_law, self._actions(task, split="ood"))
            numeric_fit = bool(
                validation_score["all_predictions_finite"]
                and validation_score["n_points"] > 0
                and validation_score["relative_rmse"] <= self.relative_tolerance
            )
            ood_fit = bool(
                ood_score["all_predictions_finite"]
                and ood_score["n_points"] >= int(SCORING_PROTOCOL["minimum_valid_ood_points"])
                and ood_score["relative_rmse"] <= self.ood_relative_tolerance
            )
            structural_recovery = structurally_equivalent(candidate.code, gt_law, params)
            mechanistic_validity = bool(structural_recovery and ood_fit)
            return {
                "validated_success": bool(numeric_fit and mechanistic_validity),
                "numeric_fit": numeric_fit,
                "ood_fit": ood_fit,
                "structural_recovery": bool(structural_recovery),
                "mechanistic_validity": mechanistic_validity,
                "equivalence_class": "canonical_ast" if structural_recovery else "none",
                "rmsle": validation_score["rmsle"],
                "relative_rmse": validation_score["relative_rmse"],
                "ood_rmsle": ood_score["rmsle"],
                "ood_relative_rmse": ood_score["relative_rmse"],
                "n_validation_points": validation_score["n_points"],
                "n_ood_points": ood_score["n_points"],
                "official_numeric_evaluator": False,
                "upstream_ground_truth_function_used": True,
                "success_definition": "numeric_fit_and_structural_recovery_and_ood",
                "symbolic_judge_used": False,
                "scoring_protocol_version": SCORING_PROTOCOL["version"],
                "error": None,
                "ground_truth": {"source": inspect.getsource(gt_law), "exposed_to_model": False, "phase": "post_submission_evaluation"},
            }
        except Exception as exc:
            return self._failure(str(exc), upstream_ground_truth_function_used=True)
