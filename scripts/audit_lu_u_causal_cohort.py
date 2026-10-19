"""Independent audit of paired LU/U public causal calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--cohort", type=Path, required=True); parser.add_argument("--run", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); parser.add_argument("--expected-model-id", default="kimi-k2.5"); args = parser.parse_args()
    plan = json.loads((args.cohort / "cohort_plan.json").read_text(encoding="utf-8")); tasks = {x["task_id"]: x for x in read_jsonl(args.cohort / "public_tasks.jsonl")}; truth = {x["task_id"]: x for x in read_jsonl(args.cohort / "causal_truth_key.jsonl")}; records = read_jsonl(args.run / "records.jsonl"); traces = read_jsonl(args.run / "provider_traces.jsonl")
    failures: list[str] = []; statuses: Counter[str] = Counter(); rows = []
    if sha256(args.cohort / "causal_truth_key.jsonl") != plan["truth_key_sha256"]: failures.append("truth_key_hash_mismatch")
    if set(tasks) != set(truth) or len(tasks) != int(plan.get("task_count", -1)): failures.append("task_truth_bijection_or_count")
    by_task: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records: by_task.setdefault(str(record.get("task_id")), {})[str(record.get("arm"))] = record
    if set(by_task) != set(tasks) or any(set(arms) != {"control", "intervention"} for arms in by_task.values()): failures.append("paired_record_bijection")
    for task_id, task in tasks.items():
        expected = truth[task_id]; item = {"task_id": task_id}; arm_results = {}
        for arm in ("control", "intervention"):
            record = by_task.get(task_id, {}).get(arm, {}); candidate = record.get("candidate"); result = "NOT_SCORED"
            if record.get("model_id") != args.expected_model_id: failures.append(f"model:{task_id}:{arm}")
            if record.get("private_labels_read") is not False or record.get("truth_key_read") is not False: failures.append(f"isolation:{task_id}:{arm}")
            if record.get("validation_error") is not None or not isinstance(candidate, dict): result = "NOT_SCORED"
            elif candidate.get("state_after") == (expected["control_state"] if arm == "control" else expected["intervention_state"]) and candidate.get("to_status") == candidate.get("state_after") and candidate.get("state_before") == "supported": result = "TRUTH_MATCH"
            else: result = "TRUTH_MISMATCH"
            statuses[f"{arm}:{result}"] += 1; arm_results[arm] = result; item[arm] = result
            if not any(t.get("task_id") == task_id and t.get("arm") == arm for t in traces): failures.append(f"trace_missing:{task_id}:{arm}")
        if arm_results.get("control") == "TRUTH_MATCH" and arm_results.get("intervention") == "TRUTH_MATCH" and expected["control_state"] != expected["intervention_state"]:
            item["validated_causal_contrast"] = True; statuses["validated_causal_contrast"] += 1
        else: item["validated_causal_contrast"] = False
        rows.append(item)
    summary = {"schema_version": 1, "audit_version": "lu-u-causal-independent-v1", "task_count": len(tasks), "record_count": len(records), "trace_count": len(traces), "status_counts": dict(sorted(statuses.items())), "task_sha256": sha256(args.cohort / "public_tasks.jsonl"), "truth_key_sha256": sha256(args.cohort / "causal_truth_key.jsonl"), "records_sha256": sha256(args.run / "records.jsonl"), "traces_sha256": sha256(args.run / "provider_traces.jsonl"), "private_labels_read": False, "truth_key_sent_to_model": False, "pooled_with_formal_g7": False, "scientific_release_allowed": False, "failures": failures, "rows": rows, "interpretation": "Validated paired contrasts are public causal calibration evidence only; they do not retroactively convert the historical LU/U observations into a formal G7 causal estimate."}
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(json.dumps(summary, ensure_ascii=False, indent=2)); return 0 if not failures else 2


if __name__ == "__main__": raise SystemExit(main())
