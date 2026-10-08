"""Common law schema and objective numeric evaluation."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
import importlib
import math
from pathlib import Path
import random
from typing import Any, Callable

import numpy as np

from ..benchmark.base import TaskSpec
from ..benchmark.task_registry import ensure_upstream_importable
from ..utils.json_protocol import ProtocolError, parse_json_object


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
    """Uses upstream numerical evaluation on a held-out evaluator-only set."""

    def __init__(self, repo_root: Path, test_points: int = 128, relative_tolerance: float = 1e-5):
        self.repo_root = Path(repo_root)
        self.test_points = int(test_points)
        self.relative_tolerance = float(relative_tolerance)

    def _actions(self, task: TaskSpec, *, split: str) -> list[dict[str, float]]:
        rng = random.Random((task.seed * 1009) + (17 if split == "validation" else 0))
        _, _, params = _task_module(task, self.repo_root)
        actions = []
        for _ in range(self.test_points):
            values = {name: 10 ** rng.uniform(-0.3, 1.5) for name in params}
            actions.append(values)
        return actions

    def evaluate(self, task: TaskSpec, candidate: LawCandidate) -> dict[str, Any]:
        try:
            module, gt_law, params = _task_module(task, self.repo_root)
            fn = _safe_function(candidate.code, params)
        except Exception as exc:
            return {"validated_success": False, "numeric_fit": False, "structural_recovery": None, "mechanistic_validity": "not_implemented", "rmsle": float("nan"), "relative_rmse": float("nan"), "error": str(exc), "official_numeric_evaluator": False}

        actions = self._actions(task, split="validation")
        y_true = np.asarray([gt_law(**action) for action in actions], dtype=float)
        try:
            y_pred = np.asarray([fn(**action) for action in actions], dtype=float)
            if not np.all(np.isfinite(y_pred)):
                raise ValueError("candidate returned non-finite predictions")
            relative_rmse = float(np.sqrt(np.mean(((y_pred - y_true) / np.maximum(np.abs(y_true), 1e-12)) ** 2)))
            rmsle = float(np.sqrt(np.mean((np.log1p(np.maximum(y_pred, 0)) - np.log1p(np.maximum(y_true, 0))) ** 2)))
            return {
                "validated_success": bool(relative_rmse <= self.relative_tolerance),
                "numeric_fit": bool(relative_rmse <= self.relative_tolerance),
                "structural_recovery": None,
                "mechanistic_validity": "not_implemented",
                "rmsle": rmsle,
                "relative_rmse": relative_rmse,
                "n_validation_points": len(actions),
                "official_numeric_evaluator": True,
                "symbolic_judge_used": False,
                "error": None,
            }
        except Exception as exc:
            return {"validated_success": False, "numeric_fit": False, "structural_recovery": None, "mechanistic_validity": "not_implemented", "rmsle": float("nan"), "relative_rmse": float("nan"), "error": str(exc), "official_numeric_evaluator": True, "symbolic_judge_used": False}
