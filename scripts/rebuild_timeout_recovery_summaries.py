#!/usr/bin/env python3
"""Rebuild per-run timeout recovery summaries from immutable recovery files.

This is deliberately independent of the live executor's in-memory futures.
It prevents reused benchmark run IDs from mixing matched LLM and Agent runs.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from retry_timeout_tasks import _is_transport_timeout


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _cost(result: dict[str, Any]) -> float:
    budget = ((result.get("metadata") or {}).get("budget") or {}).get("used") or {}
    try:
        return float(budget.get("cost_usd", 0.0))
    except (TypeError, ValueError):
        return 0.0


def rebuild(plan_path: Path) -> dict[str, Any]:
    plan = _load(plan_path)
    run_dir = Path(plan["run_dir"])
    result_paths = sorted((run_dir / "timeout_recovery" / "models").glob("*/*.json"))
    by_task: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for path in result_paths:
        try:
            result = _load(path)
        except (OSError, json.JSONDecodeError):
            continue
        task_id = str(result.get("task_id", ""))
        model_id = str(result.get("model_id", path.parent.name))
        if task_id:
            by_task[(model_id, task_id)] = (path, result)

    rows: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    for task in plan.get("tasks") or []:
        key = (str(task["model_id"]), str(task["task_id"]))
        item = by_task.get(key)
        if item is None:
            missing.append({"model_id": key[0], "task_id": key[1]})
            continue
        path, result = item
        validation = result.get("validation") or {}
        rows.append(
            {
                "task_id": key[1],
                "model_id": key[0],
                "run_id": str(plan["run_id"]),
                "run_dir": str(run_dir),
                "status": result.get("status"),
                "validation_status": validation.get("status"),
                "answer_correct": bool(validation.get("answer_correct", False)),
                "protocol_valid": result.get("protocol_valid"),
                "result_directory": str(path.parent),
                "result_file": str(path),
                "recovered_timeout": _is_transport_timeout(result),
                "cost_usd": _cost(result),
            }
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary_version": 2,
        "run_id": str(plan["run_id"]),
        "run_dir": str(run_dir),
        "source": "timeout_recovery/models",
        "task_count": len(plan.get("tasks") or []),
        "retried_count": len(rows),
        "missing_count": len(missing),
        "missing_tasks": missing,
        "results": rows,
    }
    output = run_dir / "timeout_recovery" / "timeout_recovery_summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    args = parser.parse_args()
    plans = sorted(args.benchmark_root.resolve().rglob("timeout_recovery_plan.json"))
    summaries = [rebuild(path) for path in plans]
    print(
        json.dumps(
            {
                "plans": len(plans),
                "summaries": len(summaries),
                "retried_count": sum(s["retried_count"] for s in summaries),
                "missing_count": sum(s["missing_count"] for s in summaries),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
