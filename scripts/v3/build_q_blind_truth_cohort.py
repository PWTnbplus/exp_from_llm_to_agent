"""Build a public monotonicity calibration set and seal its truth key.

The truth key is produced before any provider call and is never sent in a
model request.  This is a supplementary Q-v2 calibration cohort, not a
replacement for the frozen 92-case denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def ast(op: str, *args: Any, **extra: Any) -> dict[str, Any]:
    value: dict[str, Any] = {"op": op}
    if op == "number":
        value["value"] = extra["value"]
    elif op == "variable":
        value["name"] = extra["name"]
    else:
        value["args"] = list(args)
    return value


X = ast("variable", name="x")


TASKS: list[tuple[str, dict[str, Any], tuple[str, ...]]] = [
    ("linear_pos", ast("add", ast("mul", ast("number", value=2), X), ast("number", value=1)), ("increasing", "nondecreasing")),
    ("linear_neg", ast("add", ast("mul", ast("number", value=-3), X), ast("number", value=4)), ("decreasing", "nonincreasing")),
    ("identity", X, ("increasing", "nondecreasing")),
    ("negative_identity", ast("neg", X), ("decreasing", "nonincreasing")),
    ("constant_pos", ast("number", value=5), ("nondecreasing", "nonincreasing")),
    ("constant_neg", ast("number", value=-5), ("nondecreasing", "nonincreasing")),
    ("quadratic_pos", ast("pow", X, ast("number", value=2)), ("increasing", "nondecreasing")),
    ("quadratic_neg", ast("neg", ast("pow", X, ast("number", value=2))), ("decreasing", "nonincreasing")),
    ("linear_pos_2", ast("add", ast("mul", ast("number", value=3), X), ast("number", value=2)), ("increasing", "nondecreasing")),
    ("linear_neg_2", ast("add", ast("mul", ast("number", value=-2), X), ast("number", value=-3)), ("decreasing", "nonincreasing")),
    ("cubic_pos", ast("pow", X, ast("number", value=3)), ("increasing", "nondecreasing")),
    ("cubic_neg", ast("neg", ast("pow", X, ast("number", value=3))), ("decreasing", "nonincreasing")),
    ("linear_pos_3", ast("sub", ast("mul", ast("number", value=4), X), ast("number", value=1)), ("increasing", "nondecreasing")),
    ("linear_neg_3", ast("sub", ast("neg", ast("mul", ast("number", value=4), X)), ast("number", value=-1)), ("decreasing", "nonincreasing")),
    ("quadratic_shift_pos", ast("add", ast("pow", X, ast("number", value=2)), ast("mul", ast("number", value=2), X)), ("increasing", "nondecreasing")),
    ("quadratic_shift_neg", ast("neg", ast("add", ast("pow", X, ast("number", value=2)), ast("mul", ast("number", value=2), X))), ("decreasing", "nonincreasing")),
    ("constant_seven", ast("number", value=7), ("nondecreasing", "nonincreasing")),
    ("constant_zero", ast("number", value=0), ("nondecreasing", "nonincreasing")),
    ("quartic_pos", ast("pow", X, ast("number", value=4)), ("increasing", "nondecreasing")),
    ("quartic_neg", ast("neg", ast("pow", X, ast("number", value=4))), ("decreasing", "nonincreasing")),
    ("linear_zero_intercept", ast("add", X, ast("number", value=0)), ("increasing", "nondecreasing")),
    ("negative_zero_intercept", ast("sub", ast("number", value=0), X), ("decreasing", "nonincreasing")),
    ("constant_two", ast("number", value=2), ("nondecreasing", "nonincreasing")),
    ("constant_minus_two", ast("number", value=-2), ("nondecreasing", "nonincreasing")),
]


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tasks: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    for index, (name, expression, acceptable) in enumerate(TASKS, 1):
        task_id = f"QBT-{index:03d}-{name}"
        task = {
            "task_id": task_id,
            "expression": expression,
            "domain": {"variable": "x", "lower": 0, "upper": "infinity"},
            "public_instruction": "Generate a Q-v2 monotonicity claim for exactly this expression on the supplied domain. Determine the relation yourself.",
        }
        tasks.append(task)
        key.append({
            "task_id": task_id,
            "expected_expression_sha256": digest(expression),
            "acceptable_relations": list(acceptable),
            "derivation": "exact polynomial derivative sign on x>=0",
        })
    task_path = args.out / "public_tasks.jsonl"
    key_path = args.out / "truth_key.jsonl"
    task_path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in tasks), encoding="utf-8")
    key_path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in key), encoding="utf-8")
    plan = {
        "protocol_id": "Q_V2_BLIND_TRUTH_CALIBRATION_V1",
        "task_count": len(tasks),
        "task_sha256": hashlib.sha256(task_path.read_bytes()).hexdigest(),
        "truth_key_sha256": hashlib.sha256(key_path.read_bytes()).hexdigest(),
        "truth_key_created_before_provider_calls": True,
        "truth_key_sent_to_model": False,
        "private_labels_read": False,
        "pooled_with_frozen_q_v2": False,
        "scientific_release_allowed": False,
    }
    (args.out / "cohort_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
