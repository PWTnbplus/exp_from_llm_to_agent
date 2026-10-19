"""Independent audit for a targeted CTFlow recovery arm.

The report validates persisted task coverage, manifest identity, trace presence,
budget/redaction fields, and failure accounting.  It never upgrades a failed
task or a single arm into a scientific release or a matched pair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(batch: Path, manifest: Path, model: str, runner: str) -> dict[str, Any]:
    failures: list[str] = []
    result_path = batch / "result.json"
    if not result_path.is_file():
        return {"audit": "ctflow_recovery_structural_v1", "structural_complete": False,
                "scientific_release_allowed": False, "failures": ["missing:result.json"]}
    raw = read_json(result_path)
    expected = read_json(manifest)
    expected_ids = [str(row["task_id"]) for row in expected]
    rows = raw.get("tasks") if isinstance(raw.get("tasks"), list) else []
    if raw.get("model_id") != model:
        failures.append("model_id")
    if raw.get("runner") != runner:
        failures.append("runner")
    if raw.get("provider") != "ctflow" or raw.get("mock") is not False:
        failures.append("provider_or_mock")
    if raw.get("budget_enforced") is not True:
        failures.append("budget_enforced")
    if raw.get("manifest_sha256") != digest(manifest):
        failures.append("manifest_hash")
    ids = [str(row.get("task_id")) for row in rows]
    if ids != expected_ids:
        failures.append("task_manifest_order")
    if raw.get("task_count") != len(expected_ids) or len(rows) != len(expected_ids):
        failures.append("task_count")
    accounted_failures = sum(row.get("status") != "completed" for row in rows)
    if raw.get("task_failures") != accounted_failures:
        failures.append("failure_count")
    traces = 0
    for row in rows:
        task_dir = batch / str(row.get("output_dir", "")).replace("\\", "/")
        logs = list(task_dir.glob("logs/*.jsonl")) if task_dir.is_dir() else []
        if not logs:
            failures.append(f"missing_trace:{row.get('task_id')}")
        else:
            traces += 1
    secret_markers = 0
    unredacted_truth = 0
    for path in batch.rglob("*.jsonl"):
        text = path.read_text(encoding="utf-8", errors="replace")
        secret_markers += text.count("Bearer ")
        for line in text.splitlines():
            if "ground_truth_exposed_to_model" in line and '"[REDACTED]"' not in line:
                unredacted_truth += 1
    if secret_markers or unredacted_truth:
        failures.append("redaction")
    return {
        "audit": "ctflow_recovery_structural_v1",
        "batch": str(batch.resolve()),
        "manifest": str(manifest.resolve()),
        "model_id": model,
        "runner": runner,
        "structural_complete": not failures,
        "scientific_release_allowed": False,
        "matched_pair_verified": False,
        "failures": failures,
        "status": raw.get("status"),
        "task_count": raw.get("task_count"),
        "task_failures": raw.get("task_failures"),
        "validated_success_count": raw.get("validated_success_count"),
        "protocol_valid": raw.get("protocol_valid"),
        "evaluator_valid": raw.get("evaluator_valid"),
        "trace_count": traces,
        "actual_local_proxy_cost_usd": raw.get("cost_usd"),
        "reserved_local_proxy_cost_usd": raw.get("reserved_cost_usd"),
        "secret_marker_hits": secret_markers,
        "unredacted_ground_truth_markers": unredacted_truth,
        "note": "Targeted recovery evidence is append-only and is not merged into the frozen formal denominator.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.batch, args.manifest, args.model, args.runner)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("structural_complete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
