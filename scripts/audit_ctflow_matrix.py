"""Independent structural audit for one persisted CTFlow scientific matrix.

This audit never converts a failed arm into a pass and never makes a scientific
truth decision.  It checks that the four requested matched arms, all manifest
tasks, traces, local budget fields, and failure records are present and
consistent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_MODELS = ("qwen3.5-plus", "glm-5.2")
EXPECTED_RUNNERS = ("agent", "llm_only")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(batch: Path) -> dict[str, Any]:
    failures: list[str] = []
    summary_path = batch / "summary.json"
    manifest_path = batch / "manifest.json"
    if not summary_path.is_file():
        failures.append("missing:summary.json")
    if not manifest_path.is_file():
        failures.append("missing:manifest.json")
    summary = read_json(summary_path) if summary_path.is_file() else {}
    manifest = read_json(manifest_path) if manifest_path.is_file() else {}

    task_manifest_path = Path(__file__).resolve().parents[1] / "task_manifest.json"
    task_manifest = read_json(task_manifest_path)
    expected_task_ids = [str(row["task_id"]) for row in task_manifest]
    expected_arms = {(model, runner) for model in EXPECTED_MODELS for runner in EXPECTED_RUNNERS}
    # Use the exact two-level shape so unrelated nested artifacts cannot count.
    result_paths = sorted(
        path for model_dir in batch.iterdir() if model_dir.is_dir()
        for runner_dir in model_dir.iterdir() if runner_dir.is_dir()
        for path in [runner_dir / "result.json"] if path.is_file()
    )
    arms: dict[tuple[str, str], dict[str, Any]] = {}
    for result_path in result_paths:
        raw = read_json(result_path)
        key = (str(raw.get("model_id")), str(raw.get("runner")))
        if key in arms:
            failures.append(f"duplicate_arm:{key}")
            continue
        arms[key] = raw
        if key not in expected_arms:
            failures.append(f"unexpected_arm:{key}")

        rows = raw.get("tasks")
        if not isinstance(rows, list) or len(rows) != len(expected_task_ids):
            failures.append(f"task_count:{key}:{raw.get('task_count')}")
            rows = rows if isinstance(rows, list) else []
        ids = [str(row.get("task_id")) for row in rows]
        if ids != expected_task_ids:
            failures.append(f"task_manifest_order:{key}")
        if raw.get("manifest_sha256") != sha256(task_manifest_path):
            failures.append(f"manifest_hash:{key}")
        if raw.get("mock") is not False:
            failures.append(f"mock_arm:{key}")
        if raw.get("provider") != "ctflow":
            failures.append(f"provider:{key}")
        if raw.get("provider_billing_verified") is not False:
            failures.append(f"billing_flag:{key}")
        if raw.get("cost_interpretation") != "local_proxy_unverified_provider_billing":
            failures.append(f"cost_interpretation:{key}")
        if raw.get("budget_enforced") is not True:
            failures.append(f"budget_gate:{key}")
        if not isinstance(raw.get("cost_usd"), (int, float)) or not isinstance(raw.get("reserved_cost_usd"), (int, float)):
            failures.append(f"cost_fields:{key}")
        elif raw["cost_usd"] < 0 or raw["reserved_cost_usd"] < 0:
            failures.append(f"negative_cost:{key}")
        if raw.get("task_failures", 0) != sum(row.get("status") != "completed" for row in rows):
            failures.append(f"failure_count:{key}")

        task_root = result_path.parent / "tasks"
        trace_count = len(list(task_root.glob("*/logs/*.jsonl"))) if task_root.is_dir() else 0
        if trace_count != len(expected_task_ids):
            failures.append(f"trace_count:{key}:{trace_count}")
        for row in rows:
            # The persisted row stores a path relative to the arm output
            # directory (for example ``tasks\\000_...``), not relative to
            # the tasks directory itself.
            task_dir = result_path.parent / str(row.get("output_dir", "")).replace("\\", "/")
            if not task_dir.is_dir() or not list(task_dir.glob("logs/*.jsonl")):
                failures.append(f"missing_task_trace:{key}:{row.get('task_id')}")

    if set(arms) != expected_arms:
        failures.append(f"arm_set:{sorted(arms)}")
    if summary.get("all_paired_verified") is not False:
        failures.append("summary_pair_gate_not_false")

    total_cost = sum(float(raw.get("cost_usd", 0.0)) for raw in arms.values())
    total_reserved = sum(float(raw.get("reserved_cost_usd", 0.0)) for raw in arms.values())
    configured_cap = float(manifest.get("cost_ceiling_usd", manifest.get("max_total_cost_usd", 0.0)))
    per_arm_cap = configured_cap / len(expected_arms) if expected_arms else 0.0
    for key, raw in arms.items():
        if float(raw.get("cost_usd", 0.0)) > per_arm_cap + 1e-9 or float(raw.get("reserved_cost_usd", 0.0)) > per_arm_cap + 1e-9:
            failures.append(f"arm_cost_cap:{key}")
    if configured_cap <= 0 or total_reserved > configured_cap + 1e-9 or total_cost > configured_cap + 1e-9:
        failures.append("aggregate_cost_cap")

    secret_markers = 0
    unredacted_ground_truth = 0
    for path in batch.rglob("*.jsonl"):
        text = path.read_text(encoding="utf-8", errors="replace")
        secret_markers += text.count("Bearer ")
        for line in text.splitlines():
            if "ground_truth_exposed_to_model" in line and '"[REDACTED]"' not in line:
                unredacted_ground_truth += 1
    if secret_markers or unredacted_ground_truth:
        failures.append(f"redaction:{secret_markers}:{unredacted_ground_truth}")

    return {
        "audit": "ctflow_matrix_structural_v1",
        "batch": str(batch.resolve()),
        "batch_id": summary.get("batch_id"),
        "structural_complete": not failures,
        "scientific_release_allowed": False,
        "paired_verified": summary.get("all_paired_verified"),
        "failures": failures,
        "arms": {
            f"{model}/{runner}": {
                "status": raw.get("status"),
                "task_count": raw.get("task_count"),
                "task_failures": raw.get("task_failures"),
                "validated_success_count": raw.get("validated_success_count"),
                "protocol_valid": raw.get("protocol_valid"),
                "evaluator_valid": raw.get("evaluator_valid"),
                "cost_usd": raw.get("cost_usd"),
                "reserved_cost_usd": raw.get("reserved_cost_usd"),
            }
            for (model, runner), raw in sorted(arms.items())
        },
        "aggregate": {
            "arm_count": len(arms),
            "task_rows": sum(int(raw.get("task_count", 0)) for raw in arms.values()),
            "actual_local_proxy_cost_usd": total_cost,
            "reserved_local_proxy_cost_usd": total_reserved,
            "configured_matrix_cap_usd": configured_cap,
            "secret_marker_hits": secret_markers,
            "unredacted_ground_truth_markers": unredacted_ground_truth,
        },
        "note": "Failures and held-out validation outcomes remain evidence; this report does not claim model superiority or provider billing accuracy.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.batch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["structural_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
