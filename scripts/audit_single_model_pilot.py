"""Independent structural audit for one exact-model pilot checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


RUNNERS = ("agent", "llm_only")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(batch: Path, task_manifest: Path) -> dict[str, Any]:
    failures: list[str] = []
    result_path = batch / "result.json"
    manifest_path = batch / "manifest.json"
    if not result_path.is_file():
        failures.append("missing:result.json")
    if not manifest_path.is_file():
        failures.append("missing:manifest.json")
    result = read_json(result_path) if result_path.is_file() else {}
    manifest = read_json(manifest_path) if manifest_path.is_file() else {}
    task_rows = read_json(task_manifest) if task_manifest.is_file() else []
    expected_ids = [str(row["task_id"]) for row in task_rows]
    expected_keys = {
        (replicate, runner, task_id)
        for replicate in range(int(result.get("repeats_per_task_per_arm", 0) or 0))
        for runner in ("llm_only", "agent")
        for task_id in expected_ids
    }
    rows = result.get("rows") if isinstance(result.get("rows"), list) else []
    seen: set[tuple[int, str, str]] = set()
    if result.get("model_id") != manifest.get("model_id"):
        failures.append("model_id_mismatch")
    if result.get("provider") != "ctflow":
        failures.append("provider_not_ctflow")
    if result.get("provider_billing_verified") is not False:
        failures.append("billing_flag_not_false")
    if result.get("scientific_release_allowed") is not False:
        failures.append("release_gate_not_false")
    if result.get("manifest_sha256") != sha256(task_manifest):
        failures.append("manifest_hash_mismatch")
    if result.get("expected_runs") != len(expected_keys):
        failures.append("expected_run_count_mismatch")
    if result.get("registered_runs") != len(rows) or len(rows) != len(expected_keys):
        failures.append("registered_run_count_mismatch")
    for row in rows:
        try:
            key = (int(row["replicate_index"]), str(row["runner"]), str(row["task_id"]))
        except (KeyError, TypeError, ValueError):
            failures.append("malformed_row_key")
            continue
        if key in seen:
            failures.append(f"duplicate_row:{key}")
        seen.add(key)
        if key not in expected_keys:
            failures.append(f"unexpected_row:{key}")
        if row.get("runner") not in RUNNERS:
            failures.append(f"unexpected_runner:{key}")
        output_dir = batch / str(row.get("output_dir", "")).replace("\\", "/")
        if not output_dir.is_dir():
            failures.append(f"missing_task_dir:{key}")
            continue
        traces = list((output_dir / "logs").glob("*.jsonl")) if (output_dir / "logs").is_dir() else []
        if not traces:
            failures.append(f"missing_trace:{key}")
        result_files = [path for path in output_dir.glob("*.json") if path.name != "task_failure.json"]
        failure_file = output_dir / "task_failure.json"
        if not result_files and not failure_file.is_file():
            failures.append(f"missing_result_or_failure_record:{key}")
        for name in ("cost_usd", "reserved_cost_usd"):
            value = row.get(name)
            if not isinstance(value, (int, float)) or value < 0:
                failures.append(f"invalid_{name}:{key}")
        if row.get("status") != "completed" and row.get("validated_success") is True:
            failures.append(f"failed_row_claims_success:{key}")
    if seen != expected_keys:
        failures.append("row_key_set_mismatch")
    if result.get("task_failures") != sum(row.get("status") != "completed" for row in rows):
        failures.append("failure_count_mismatch")
    if result.get("validated_success_count") != sum(bool(row.get("validated_success")) for row in rows):
        failures.append("success_count_mismatch")
    actual = sum(float(row.get("cost_usd", 0.0) or 0.0) for row in rows)
    reserved = sum(float(row.get("reserved_cost_usd", 0.0) or 0.0) for row in rows)
    if abs(actual - float(result.get("actual_cost_usd", -1.0))) > 1e-9:
        failures.append("actual_cost_sum_mismatch")
    if abs(reserved - float(result.get("reserved_cost_usd", -1.0))) > 1e-9:
        failures.append("reserved_cost_sum_mismatch")
    cap = float(result.get("max_cost_usd", -1.0))
    if result.get("budget_enforced") is not True or cap <= 0 or actual > cap + 1e-9 or reserved > cap + 1e-9:
        failures.append("budget_gate")
    secret_hits = 0
    unredacted_truth_hits = 0
    for path in batch.rglob("*.jsonl"):
        text = path.read_text(encoding="utf-8", errors="replace")
        secret_hits += text.count("Bearer ")
        for line in text.splitlines():
            if "ground_truth_exposed_to_model" in line and '"[REDACTED]"' not in line:
                unredacted_truth_hits += 1
    if secret_hits or unredacted_truth_hits:
        failures.append(f"redaction:{secret_hits}:{unredacted_truth_hits}")
    return {
        "audit": "single_model_pilot_structural_v1",
        "batch": str(batch.resolve()),
        "model_id": result.get("model_id"),
        "structural_complete": not failures,
        "scientific_release_allowed": False,
        "failures": failures,
        "rows": {
            "expected": len(expected_keys),
            "registered": len(rows),
            "unique": len(seen),
            "trace_directories": sum(1 for row in rows if (batch / str(row.get("output_dir", "")).replace("\\", "/") / "logs").is_dir()),
        },
        "outcomes": {
            "task_failures": result.get("task_failures"),
            "validated_success_count": result.get("validated_success_count"),
            "actual_local_proxy_cost_usd": actual,
            "reserved_local_proxy_cost_usd": reserved,
            "configured_cap_usd": cap,
            "secret_marker_hits": secret_hits,
            "unredacted_ground_truth_markers": unredacted_truth_hits,
        },
        "note": "This is an independent structural audit. Pilot outcomes are non-confirmatory and provider billing/model-weight identity remain unverified.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.batch, args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["structural_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
