"""Deterministic answer verification with explicit model/error categories."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import sympy as sp

from .schema import load_benchmark


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _close(a: Any, b: Any, tolerance: float) -> bool:
    if not (_is_number(a) and _is_number(b)):
        return False
    if not math.isfinite(float(a)) or not math.isfinite(float(b)):
        return a == b
    return abs(float(a) - float(b)) <= tolerance * max(1.0, abs(float(b)))


def _parse_expression(text: str) -> Any:
    names = set(re.findall(r"\b[A-Za-z_]\w*\b", text))
    known = {"exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "pi": sp.pi, "E": sp.E}
    local_dict = {name: known.get(name, sp.Symbol(name)) for name in names}
    return sp.sympify(text, locals=local_dict)


def _expression_equal(actual: str, expected: str) -> bool:
    try:
        def relation(text: str) -> Any:
            if text.count("=") == 1:
                left, right = text.split("=", 1)
                return _parse_expression(left) - _parse_expression(right)
            return _parse_expression(text)
        return bool(sp.simplify(relation(actual) - relation(expected)) == 0)
    except (TypeError, ValueError, SyntaxError, sp.SympifyError):
        return False


def _compare(expected: Any, actual: Any, *, path: str, expression_fields: set[str], unordered_fields: set[str], tolerance: float, errors: list[str]) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            errors.append(f"{path}: expected object")
            return
        for key, value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing")
                continue
            _compare(value, actual[key], path=f"{path}.{key}", expression_fields=expression_fields, unordered_fields=unordered_fields, tolerance=tolerance, errors=errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            errors.append(f"{path}: list length/type mismatch")
            return
        if path.rsplit(".", 1)[-1] in unordered_fields:
            remaining = list(actual)
            for index, item in enumerate(expected):
                matched = False
                for candidate_index, candidate in enumerate(remaining):
                    local: list[str] = []
                    _compare(item, candidate, path=f"{path}[{index}]", expression_fields=expression_fields, unordered_fields=unordered_fields, tolerance=tolerance, errors=local)
                    if not local:
                        remaining.pop(candidate_index)
                        matched = True
                        break
                if not matched:
                    errors.append(f"{path}[{index}]: no matching item")
            return
        for index, (want, got) in enumerate(zip(expected, actual)):
            _compare(want, got, path=f"{path}[{index}]", expression_fields=expression_fields, unordered_fields=unordered_fields, tolerance=tolerance, errors=errors)
        return
    if _is_number(expected):
        if not _close(expected, actual, tolerance):
            errors.append(f"{path}: expected {expected!r}, got {actual!r}")
        return
    if isinstance(expected, str) and path.rsplit(".", 1)[-1] in expression_fields:
        if not isinstance(actual, str) or not _expression_equal(actual, expected):
            errors.append(f"{path}: expressions are not equivalent")
        return
    if expected != actual:
        errors.append(f"{path}: expected {expected!r}, got {actual!r}")


def extract_final_answer(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, dict) and isinstance(candidate.get("final_answer"), dict):
        return candidate["final_answer"]
    if isinstance(candidate, dict):
        return candidate
    raise ValueError("candidate answer must be a JSON object")


def verify_candidate(task_id: str, candidate: Any, *, data_dir: Path | None = None, redact_errors: bool = False) -> dict[str, Any]:
    try:
        public, answers, _ = load_benchmark(data_dir)
        if task_id not in answers:
            return {"status": "INFRASTRUCTURE_ERROR", "task_id": task_id, "errors": ["unknown task ID"]}
        answer = answers[task_id]
        expected = answer["ground_truth"]["answer"]
        checker = answer["checker"]
        actual = extract_final_answer(candidate)
        errors: list[str] = []
        _compare(expected, actual, path="final_answer", expression_fields=set(checker.get("expression_fields", [])), unordered_fields=set(checker.get("unordered_fields", [])), tolerance=float(checker.get("tolerance", 1e-6)), errors=errors)
        reported_errors = ["validation mismatch at " + error.split(":", 1)[0] for error in errors] if redact_errors else errors
        return {
            "status": "PASS" if not errors else "MODEL_ERROR",
            "task_id": task_id,
            "difficulty_level": next(row["difficulty_level"] for row in public if row["task_id"] == task_id),
            "domain": next(row["domain"] for row in public if row["task_id"] == task_id),
            "answer_correct": not errors,
            "errors": reported_errors,
            "validator": "structured-numeric-sympy-v1",
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return {"status": "VALIDATOR_ERROR", "task_id": task_id, "errors": [f"{type(exc).__name__}: {exc}"]}
