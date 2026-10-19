"""Build a public paired control/intervention LU/U truth cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


TASKS = [
    ("linear_pos_to_neg", "f(x)=2*x+1 is increasing for x>=0", "f(x)=-2*x+1", "refuted"),
    ("linear_pos2_to_neg", "f(x)=x-3 is increasing for x>=0", "f(x)=-x-3", "refuted"),
    ("linear_neg_to_pos", "f(x)=-2*x+1 is decreasing for x>=0", "f(x)=2*x+1", "refuted"),
    ("identity_neg_to_pos", "f(x)=-x is decreasing for x>=0", "f(x)=x", "refuted"),
    ("zero_nondec_to_neg", "f(x)=0 is nondecreasing for x>=0", "f(x)=-x", "refuted"),
    ("zero_noninc_to_pos", "f(x)=0 is nonincreasing for x>=0", "f(x)=x", "refuted"),
    ("square_pos_to_neg", "f(x)=x^2 is increasing for x>=0", "f(x)=-x^2", "refuted"),
    ("square_neg_to_pos", "f(x)=-x^2 is decreasing for x>=0", "f(x)=x^2", "refuted"),
    ("intercept_only_pos", "f(x)=3*x+2 is increasing for x>=0", "f(x)=3*x+9", "supported"),
    ("intercept_only_neg", "f(x)=-3*x+2 is decreasing for x>=0", "f(x)=-3*x+5", "supported"),
    ("constant_nondec", "f(x)=2 is nondecreasing for x>=0", "f(x)=-2", "supported"),
    ("constant_noninc", "f(x)=-2 is nonincreasing for x>=0", "f(x)=5", "supported"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--task-id", action="append", help="optional task ID filter; repeat for a targeted recovery")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    wanted = set(args.task_id or [])
    all_task_ids = {f"LUCT-{i:03d}-{name}" for i, (name, _before, _after, _state) in enumerate(TASKS, 1)}
    if wanted - all_task_ids:
        raise ValueError(f"unknown task IDs: {sorted(wanted - all_task_ids)}")
    tasks = []; key = []
    for i, (name, before, after, intervention_state) in enumerate(TASKS, 1):
        task_id = f"LUCT-{i:03d}-{name}"
        if wanted and task_id not in wanted:
            continue
        if "nondecreasing" in before:
            relation = "nondecreasing"
        elif "nonincreasing" in before:
            relation = "nonincreasing"
        elif "increasing" in before:
            relation = "increasing"
        elif "decreasing" in before:
            relation = "decreasing"
        else:
            raise ValueError(f"cannot infer monotonicity relation from {before!r}")
        intervention_claim = f"{after} is {relation} for x>=0"
        tasks.append({
            "task_id": task_id, "claim_id": f"{task_id}:claim", "domain": "x>=0",
            "control_claim": before, "intervention_claim": intervention_claim,
            "public_intervention": f"Replace the public model only as shown: {intervention_claim}. Keep the domain and claim type fixed.",
        })
        key.append({"task_id": task_id, "control_state": "supported", "intervention_state": intervention_state, "derivation": "exact derivative sign of the displayed polynomial on x>=0"})
    task_path = args.out / "public_tasks.jsonl"; key_path = args.out / "causal_truth_key.jsonl"
    task_path.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in tasks), encoding="utf-8")
    key_path.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in key), encoding="utf-8")
    plan = {
        "protocol_id": "LU_U_PUBLIC_CAUSAL_CALIBRATION_V2" if wanted else "LU_U_PUBLIC_CAUSAL_CALIBRATION_V1",
        "task_count": len(tasks), "all_task_count": len(TASKS),
        "selected_task_ids": [task["task_id"] for task in tasks],
        "task_sha256": sha256(task_path), "truth_key_sha256": sha256(key_path),
        "truth_key_created_before_provider_calls": True, "truth_key_sent_to_model": False,
        "private_labels_read": False, "pooled_with_formal_g7": False, "scientific_release_allowed": False,
    }
    (args.out / "cohort_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
