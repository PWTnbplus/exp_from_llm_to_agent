#!/usr/bin/env python3
"""Read-only structural audit for existing theory-benchmark G1/G4 runs.

This audit intentionally never reads the private answer key and never modifies
existing result files.  It distinguishes canonical direct results from retry
directories and reports integrity/protocol/transport problems without treating
model errors as scientific failures.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def expected_ids(data_dir: Path, level: int) -> set[str]:
    payload = load_json(data_dir / "public_tasks.json")
    tasks = payload if isinstance(payload, list) else (payload or {}).get("tasks", [])
    prefixes = (f"TB-L{level}-", f"TC-L{level}-")
    return {
        str(task.get("task_id"))
        for task in tasks
        if isinstance(task, dict) and str(task.get("task_id", "")).startswith(prefixes)
    }


def audit_model(model_dir: Path, mode: str, expected: set[str]) -> dict[str, Any]:
    files = sorted(model_dir.glob(f"{mode}__*.json")) if model_dir.is_dir() else []
    statuses: Counter[str] = Counter()
    validations: Counter[str] = Counter()
    task_ids: list[str] = []
    malformed: list[str] = []
    missing_traces: list[str] = []
    wrong_group: list[str] = []
    model_mismatch: list[str] = []
    provider_error_traces = 0
    timeout_traces = 0
    json_failures = 0
    schema_failures = 0
    protocol_invalid = 0
    evaluator_invalid = 0
    credential_hits = 0
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if re.search(
            r"(?:\bsk-[A-Za-z0-9_-]{12,}|\bBearer\s+[A-Za-z0-9._~+/=-]{12,}|"
            r"[\"'](?:api[_-]?key|authorization|access[_-]?token)[\"']\s*:\s*[\"'][^\"']+[\"'])",
            raw,
            re.IGNORECASE,
        ):
            credential_hits += 1
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            malformed.append(path.name)
            continue
        task_id = str(result.get("task_id", ""))
        task_ids.append(task_id)
        statuses[str(result.get("status"))] += 1
        validation = result.get("validation") or {}
        validations[str(validation.get("status"))] += 1
        if result.get("group") != mode or result.get("mode") != mode:
            wrong_group.append(path.name)
        if str(result.get("model_id")) != model_dir.name:
            model_mismatch.append(path.name)
        if result.get("protocol_valid") is False:
            protocol_invalid += 1
        if result.get("evaluator_valid") is False:
            evaluator_invalid += 1
        errors = [str(error) for error in validation.get("errors") or []]
        if any("jsondecodeerror" in error.lower() for error in errors):
            json_failures += 1
        if any("schema" in error.lower() for error in errors):
            schema_failures += 1
        for trace in (result.get("metadata") or {}).get("provider_trace") or []:
            response = trace.get("response") or {}
            error_text = str(response.get("error") or "")
            content = str(response.get("content") or "")
            if error_text or any(token in content.lower() for token in ("401", "403", "503", "provider error")):
                provider_error_traces += 1
            if "timeout" in error_text.lower() or "timed out" in error_text.lower():
                timeout_traces += 1
        trace_path = result.get("trace_path")
        if isinstance(trace_path, str) and not (model_dir / trace_path).exists():
            missing_traces.append(path.name)
    duplicate_count = len(task_ids) - len(set(task_ids))
    missing = sorted(expected - set(task_ids))
    unexpected = sorted(set(task_ids) - expected)
    return {
        "model": model_dir.name,
        "result_files": len(files),
        "expected_result_files": len(expected),
        "task_ids": len(task_ids),
        "duplicate_task_ids": duplicate_count,
        "missing_task_ids": missing,
        "unexpected_task_ids": unexpected,
        "malformed_result_files": malformed,
        "missing_trace_files": missing_traces,
        "wrong_group_or_mode": wrong_group,
        "model_id_mismatch": model_mismatch,
        "credential_pattern_hits": credential_hits,
        "provider_error_traces": provider_error_traces,
        "timeout_traces": timeout_traces,
        "json_parse_failures": json_failures,
        "schema_failures": schema_failures,
        "protocol_invalid": protocol_invalid,
        "evaluator_invalid": evaluator_invalid,
        "status_counts": dict(statuses),
        "validation_status_counts": dict(validations),
        "structurally_complete": (
            len(files) == len(expected)
            and not malformed
            and duplicate_count == 0
            and not missing
            and not unexpected
            and not missing_traces
            and not wrong_group
            and not model_mismatch
            and credential_hits == 0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    for run in sorted(args.benchmark_root.glob("*/*/*/run-*")):
        manifest = load_json(run / "run_manifest.json")
        if not isinstance(manifest, dict):
            continue
        mode = str(manifest.get("mode"))
        level = int(manifest.get("difficulty_level") or 0)
        if mode not in {"G1", "G4"} or level not in {1, 2, 3}:
            continue
        expected = expected_ids(args.data_dir, level)
        models = [str(model) for model in manifest.get("models") or []]
        model_rows = [audit_model(run / "models" / model, mode, expected) for model in models]
        row = {
            "run": str(run),
            "mode": mode,
            "level": level,
            "manifest_models": models,
            "models": model_rows,
            "all_models_structurally_complete": all(item["structurally_complete"] for item in model_rows),
        }
        rows.append(row)
        for item in model_rows:
            for key in (
                "result_files", "duplicate_task_ids", "provider_error_traces", "timeout_traces",
                "json_parse_failures", "schema_failures", "protocol_invalid", "evaluator_invalid",
            ):
                totals[key] += int(item[key])
            totals["malformed_result_files"] += len(item["malformed_result_files"])
            totals["missing_task_ids"] += len(item["missing_task_ids"])
            totals["unexpected_task_ids"] += len(item["unexpected_task_ids"])
            totals["missing_trace_files"] += len(item["missing_trace_files"])
            totals["wrong_group_or_mode"] += len(item["wrong_group_or_mode"])
            totals["model_id_mismatch"] += len(item["model_id_mismatch"])
            totals["credential_pattern_hits"] += int(item["credential_pattern_hits"])
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_root": str(args.benchmark_root.resolve()),
        "data_dir": str(args.data_dir.resolve()),
        "answer_key_read": False,
        "canonical_direct_results_only": True,
        "run_count": len(rows),
        "runs_with_structural_problems": sum(not row["all_models_structurally_complete"] for row in rows),
        "totals": dict(totals),
        "runs": rows,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("run_count", "runs_with_structural_problems", "totals")}, ensure_ascii=False))
    for row in rows:
        if not row["all_models_structurally_complete"]:
            print(json.dumps({"run": row["run"], "mode": row["mode"], "level": row["level"], "models": row["models"]}, ensure_ascii=False))
    return 0 if report["runs_with_structural_problems"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
