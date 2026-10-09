#!/usr/bin/env python3
"""Create a read-only structural audit for a DeepSeek theory-batch run.

The audit intentionally reads only generated result/trace files and never reads
the private benchmark answer key.  It reports protocol/evaluator outcomes and
the local cost proxy recorded by the provider trace; it is not a scientific
performance claim.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


MODELS = (
    "deepseek-r1-distill-qwen-1.5b",
    "deepseek-v3.2",
    "deepseek-v4.1-flash",
    "deepseek-r1-distill-qwen-14b",
    "deepseek-r1-distill-qwen-32b",
    "deepseek-r1-distill-qwen-7b",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--level", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--expected-tasks", type=int, default=100)
    return parser.parse_args()


def add_usage(total: dict[str, float], result: dict[str, Any]) -> None:
    metadata = result.get("metadata") or {}
    for trace in metadata.get("provider_trace") or []:
        usage = ((trace.get("response") or {}).get("usage") or {})
        for name in ("input_tokens", "output_tokens"):
            value = usage.get(name)
            if isinstance(value, (int, float)):
                total[name] += value
        value = usage.get("cost_usd")
        if isinstance(value, (int, float)):
            total["cost_usd"] += value


def audit_model(model_dir: Path, level: int, expected: int) -> dict[str, Any]:
    files = sorted(model_dir.glob("G1__*.json"))
    statuses: Counter[str] = Counter()
    validation_statuses: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    usage = {"input_tokens": 0.0, "output_tokens": 0.0, "cost_usd": 0.0}
    task_ids: list[str] = []
    malformed: list[str] = []
    missing_traces: list[str] = []
    key_hits = 0

    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        key_hits += len(re.findall(r"sk-[A-Za-z0-9]", raw))
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            malformed.append(path.name)
            continue
        task_id = result.get("task_id")
        if isinstance(task_id, str):
            task_ids.append(task_id)
        statuses[str(result.get("status"))] += 1
        validation = result.get("validation") or {}
        validation_statuses[str(validation.get("status"))] += 1
        for error in validation.get("errors") or []:
            errors[str(error)] += 1
        add_usage(usage, result)
        trace_path = result.get("trace_path")
        if isinstance(trace_path, str) and not (model_dir / trace_path).exists():
            missing_traces.append(path.name)

    duplicates = len(task_ids) - len(set(task_ids))
    expected_prefixes = (f"TB-L{level}-", f"TC-L{level}-")
    wrong_level = sorted(
        task_id for task_id in task_ids if not task_id.startswith(expected_prefixes)
    )
    complete = (
        len(files) == expected
        and not malformed
        and len(task_ids) == expected
        and duplicates == 0
        and not missing_traces
        and not wrong_level
        and key_hits == 0
    )
    return {
        "model_id": model_dir.name,
        "result_files": len(files),
        "task_ids": len(task_ids),
        "duplicate_task_ids": duplicates,
        "wrong_level_task_ids": wrong_level,
        "malformed_result_files": malformed,
        "missing_trace_files": missing_traces,
        "status_counts": dict(statuses),
        "validation_status_counts": dict(validation_statuses),
        "validation_error_counts": dict(errors),
        "usage_totals": usage,
        "credential_pattern_hits": key_hits,
        "complete_structurally": complete,
    }


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    models = [audit_model(run_dir / "models" / model, args.level, args.expected_tasks) for model in MODELS]
    total = {
        "result_files": sum(row["result_files"] for row in models),
        "expected_result_files": len(MODELS) * args.expected_tasks,
        "input_tokens": sum(row["usage_totals"]["input_tokens"] for row in models),
        "output_tokens": sum(row["usage_totals"]["output_tokens"] for row in models),
        "cost_usd_proxy": sum(row["usage_totals"]["cost_usd"] for row in models),
    }
    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "benchmark": "theory_benchmark_v2",
        "level": args.level,
        "mode": "G1",
        "answer_key_read": False,
        "cost_interpretation": "Recorded provider usage cost_usd using the run's local input/output proxy; CTFlow billing was not available in the provider catalog.",
        "models": models,
        "totals": total,
        "all_models_structurally_complete": all(row["complete_structurally"] for row in models),
    }
    output = run_dir / "independent_readonly_audit.json"
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))
    return 0 if audit["all_models_structurally_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
