#!/usr/bin/env python3
"""Read-only structural audit for a complete G2/G3 theory matrix.

This audit never reads the private answer key.  It checks task coverage,
duplicate IDs, mode/group consistency, trace paths, credential leakage, and
the recorded protocol/evaluator outcomes.  A provider or model-format failure
is reported as an outcome; it is not silently converted into a missing row.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


SECRET_RE = re.compile(r"(?i)\b(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def usage_from(result: dict[str, Any]) -> dict[str, float]:
    total = {"input_tokens": 0.0, "output_tokens": 0.0, "cost_usd": 0.0}
    for trace in (result.get("metadata") or {}).get("provider_trace") or []:
        usage = ((trace.get("response") or {}).get("usage") or {})
        for key in total:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                total[key] += float(value)
    return total


def counter_rows(values: Counter[str]) -> list[dict[str, Any]]:
    """Serialize counters without case-insensitive JSON key collisions.

    PowerShell's JSON parser treats property names case-insensitively.  A
    dictionary such as ``{"x_star": 1, "X_star": 1}`` is valid for Python's
    parser but rejected by that parser as a duplicate property.  Lists keep
    the original error labels and are portable across JSON implementations.
    """
    return [
        {"key": key, "count": count}
        for key, count in sorted(values.items(), key=lambda item: item[0])
    ]


def audit_model(model_dir: Path, mode: str, expected_ids: set[str]) -> dict[str, Any]:
    files = sorted(model_dir.glob(f"{mode}__*.json"))
    task_ids: list[str] = []
    statuses: Counter[str] = Counter()
    validation_statuses: Counter[str] = Counter()
    validation_errors: Counter[str] = Counter()
    usage = {"input_tokens": 0.0, "output_tokens": 0.0, "cost_usd": 0.0}
    malformed: list[str] = []
    missing_traces: list[str] = []
    wrong_group: list[str] = []
    wrong_mode: list[str] = []
    credential_hits = 0
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        credential_hits += len(SECRET_RE.findall(raw))
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            malformed.append(path.name)
            continue
        task_id = str(result.get("task_id"))
        task_ids.append(task_id)
        statuses[str(result.get("status"))] += 1
        validation = result.get("validation") or {}
        validation_statuses[str(validation.get("status"))] += 1
        for error in validation.get("errors") or []:
            validation_errors[str(error)] += 1
        if result.get("group") != mode:
            wrong_group.append(path.name)
        if result.get("mode") != mode:
            wrong_mode.append(path.name)
        trace_path = result.get("trace_path")
        if not isinstance(trace_path, str) or not (model_dir / trace_path).is_file():
            missing_traces.append(path.name)
        current = usage_from(result)
        for key in usage:
            usage[key] += current[key]
    observed = set(task_ids)
    missing_ids = sorted(expected_ids - observed)
    unexpected_ids = sorted(observed - expected_ids)
    duplicates = len(task_ids) - len(observed)
    return {
        "model_id": model_dir.name,
        "result_files": len(files),
        "expected_result_files": len(expected_ids),
        "task_ids": len(task_ids),
        "duplicate_task_ids": duplicates,
        "missing_task_ids": missing_ids,
        "unexpected_task_ids": unexpected_ids,
        "malformed_result_files": malformed,
        "missing_trace_files": missing_traces,
        "wrong_group_files": wrong_group,
        "wrong_mode_files": wrong_mode,
        "status_counts": counter_rows(statuses),
        "validation_status_counts": counter_rows(validation_statuses),
        "validation_error_counts": counter_rows(validation_errors),
        "usage_totals": usage,
        "credential_pattern_hits": credential_hits,
        "complete_structurally": (
            len(files) == len(expected_ids)
            and len(task_ids) == len(expected_ids)
            and duplicates == 0
            and not missing_ids
            and not unexpected_ids
            and not malformed
            and not missing_traces
            and not wrong_group
            and not wrong_mode
            and credential_hits == 0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    manifest = read_json(run_dir / "run_manifest.json")
    mode = str(manifest["mode"])
    if mode not in {"G2", "G3"}:
        raise SystemExit("this audit only accepts G2 or G3")
    public = read_json(args.data_dir.resolve() / "public_tasks.json")
    expected_ids = {str(row["task_id"]) for row in public[: int(manifest.get("tasks_per_model", len(public)))]}
    model_rows = manifest.get("models") or []
    model_ids = [str(row.get("model_id", row)) if isinstance(row, dict) else str(row) for row in model_rows]
    models = [audit_model(run_dir / "models" / model_id, mode, expected_ids) for model_id in model_ids]
    totals = {
        "result_files": sum(row["result_files"] for row in models),
        "expected_result_files": len(models) * len(expected_ids),
        "input_tokens": sum(row["usage_totals"]["input_tokens"] for row in models),
        "output_tokens": sum(row["usage_totals"]["output_tokens"] for row in models),
        "cost_usd_proxy": sum(row["usage_totals"]["cost_usd"] for row in models),
    }
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "mode": mode,
        "group": manifest.get("group"),
        "answer_key_read": False,
        "models": models,
        "totals": totals,
        "all_models_structurally_complete": all(row["complete_structurally"] for row in models),
    }
    output = run_dir / "independent_readonly_audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["all_models_structurally_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
