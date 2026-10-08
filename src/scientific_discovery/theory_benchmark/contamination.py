"""Training-data contamination controls for the 100-task theory suite.

This module does not claim to detect what a model saw during pretraining. It
records risk strata and provides private, seed-dependent stress cases so that
public benchmark performance is not mistaken for contamination-free evidence.
Private answers remain in the evaluator-owned return value and are never part
of the model prompt or ordinary run result.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random
from typing import Any

from ..utils.json_protocol import canonical_json


STRATA = ("classical", "structure_transform", "private_dynamic")
LEAKAGE_MARKERS = ("ground_truth", "verification_code", "answer_key", "verification_status")


def public_task_hash(task: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(task).encode("utf-8")).hexdigest()


def _ordered(public_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(public_tasks, key=lambda row: str(row["task_id"]))


def risk_strata(public_tasks: list[dict[str, Any]]) -> dict[str, str]:
    """Assign a fixed, auditable risk-control stratum without using outcomes."""

    rows = _ordered(public_tasks)
    n = len(rows)
    counts = (math.ceil(n * 0.4), math.floor(n * 0.3), n - math.ceil(n * 0.4) - math.floor(n * 0.3))
    result: dict[str, str] = {}
    start = 0
    for stratum, count in zip(STRATA, counts):
        for row in rows[start:start + count]:
            result[str(row["task_id"])] = stratum
        start += count
    return result


def contamination_manifest(public_tasks: list[dict[str, Any]], *, version: str) -> dict[str, Any]:
    strata = risk_strata(public_tasks)
    return {
        "version": "contamination-control-v1",
        "benchmark_version": version,
        "task_count": len(public_tasks),
        "strata_counts": {name: sum(value == name for value in strata.values()) for name in STRATA},
        "task_strata": strata,
        "public_task_hashes": {row["task_id"]: public_task_hash(row) for row in public_tasks},
        "classical_caveat": "Classical items remain contamination-risk exposed; no detector result is claimed.",
        "private_dynamic_caveat": "Private dynamic cases require an operator-provided seed and are not public benchmark scores.",
    }


def assert_public_task_safe(task: dict[str, Any]) -> None:
    text = canonical_json(task).lower()
    for marker in LEAKAGE_MARKERS:
        if marker in text:
            raise AssertionError(f"public task contains answer marker: {marker}")


@dataclass(frozen=True)
class PrivateDynamicCase:
    public: dict[str, Any]
    answer: dict[str, Any]
    source_task_id: str
    seed_fingerprint: str


def generate_private_dynamic_case(task: dict[str, Any], *, seed: str) -> PrivateDynamicCase:
    """Generate a private affine reasoning case using a secret run seed.

    The generated answer is intentionally returned separately to the evaluator
    and is never serialized by the standard theory runner.
    """

    if not seed:
        raise ValueError("private dynamic generation requires a non-empty seed")
    assert_public_task_safe(task)
    fingerprint = hashlib.sha256(f"{seed}:{task['task_id']}".encode("utf-8")).hexdigest()
    rng = random.Random(fingerprint)
    a = rng.randint(2, 19)
    b = rng.randint(-9, 9)
    x = rng.randint(1, 12)
    task_id = f"private:{task['task_id']}:{fingerprint[:12]}"
    public = {
        "task_id": task_id,
        "difficulty_level": task["difficulty_level"],
        "domain": task["domain"],
        "subdomain": "private dynamic contamination stress test",
        "theory_name": "seeded affine transformation",
        "theoretical_background": "A private seed-dependent synthetic mathematical instance.",
        "assumptions": ["The generated coefficients are valid real numbers."],
        "problem_statement": f"For the private model y = a*x + b, calculate y at x={x}.",
        "mathematical_model": "y = a*x + b",
        "given_parameters": {"a": a, "b": b, "x": x},
        "expected_reasoning": ["Use the displayed model and supplied value only."],
        "difficulty_justification": "Private seed-dependent instance; not a public score.",
        "estimated_reasoning_steps": 2,
        "source_type": "Private Dynamic Synthetic Mathematical Model",
        "source_reference": "Generated at evaluation time from an operator-provided seed.",
    }
    answer = {"task_id": task_id, "ground_truth": {"answer": {"y": a * x + b, "formula": "a*x+b"}}}
    return PrivateDynamicCase(public, answer, str(task["task_id"]), fingerprint[:16])


def generate_private_dynamic_cases(public_tasks: list[dict[str, Any]], *, seed: str) -> list[PrivateDynamicCase]:
    strata = risk_strata(public_tasks)
    selected = [row for row in _ordered(public_tasks) if strata[row["task_id"]] == "private_dynamic"]
    return [generate_private_dynamic_case(row, seed=seed) for row in selected]
