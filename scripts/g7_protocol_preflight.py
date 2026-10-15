#!/usr/bin/env python3
"""Preflight the model-facing G7 protocol without making provider calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_g7_failure_localization import case_prompt


FORBIDDEN_MODEL_KEYS = (
    "expected_decision",
    "oracle_affected_claim_ids",
    "correct_revised_claim",
    "private_oracle",
    "g6_private_oracle",
)
ROUTING_METADATA_KEYS = ("cf_type", "theory_family_id")


def readl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def key_hits(text: str, keys: tuple[str, ...]) -> dict[str, int]:
    return {key: text.count(key) for key in keys if key in text}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker-count", type=int, default=16)
    args = parser.parse_args()

    public_rows = readl(args.public)
    label_rows = readl(args.labels)
    plan_rows = readl(args.plan)
    public = {row.get("case_id"): row for row in public_rows}
    labels = {row.get("case_id"): row for row in label_rows}
    prompt_text = "\n".join(
        case_prompt(public[row["case_id"]])
        for row in plan_rows
        if row.get("case_id") in public
    )
    missing_cases = sorted({row.get("case_id") for row in plan_rows if row.get("case_id") not in public})
    missing_labels = sorted({row.get("case_id") for row in plan_rows if row.get("case_id") not in labels})
    duplicate_plan_ids = len(plan_rows) - len({row.get("run_id") for row in plan_rows})
    errors: list[str] = []
    if not public_rows or not label_rows or not plan_rows:
        errors.append("public_labels_plan_must_be_nonempty")
    if missing_cases:
        errors.append("plan_case_missing_from_public")
    if missing_labels:
        errors.append("plan_case_missing_from_labels")
    if duplicate_plan_ids:
        errors.append("duplicate_run_id")
    if args.worker_count < 1 or args.worker_count > 16:
        errors.append("worker_count_out_of_range")
    routing_hits = key_hits(prompt_text, ROUTING_METADATA_KEYS)
    forbidden_hits = key_hits(prompt_text, FORBIDDEN_MODEL_KEYS)
    if routing_hits:
        errors.append("routing_metadata_in_model_prompt")
    if forbidden_hits:
        errors.append("private_oracle_metadata_in_model_prompt")
    report = {
        "audit_version": "g7-protocol-preflight-v1",
        "provider_calls_made": False,
        "formal_run_allowed_by_protocol": not errors,
        "errors": errors,
        "counts": {
            "public_cases": len(public_rows),
            "labels": len(label_rows),
            "plan_rows": len(plan_rows),
            "missing_cases": len(missing_cases),
            "missing_labels": len(missing_labels),
            "duplicate_run_ids": duplicate_plan_ids,
            "unique_checkpoint_ids": len({row.get("checkpoint_id") for row in plan_rows}),
        },
        "routing_metadata_model_prompt_hits": routing_hits,
        "forbidden_model_prompt_hits": forbidden_hits,
        "input_hashes": {
            "public": sha256(args.public),
            "labels": sha256(args.labels),
            "plan": sha256(args.plan),
        },
        "runner_contract": "scripts/run_g7_failure_localization.py::case_prompt",
        "scientific_truth_decision_made": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
