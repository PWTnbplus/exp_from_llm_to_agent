#!/usr/bin/env python3
"""Retry format-failed benchmark tasks without touching raw or timeout data."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from scientific_discovery.models.provider import OpenAICompatibleProvider
from scientific_discovery.theory_benchmark.runner import run_task

from retry_timeout_tasks import _is_transport_timeout


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _mode(value: str, manifest: dict[str, Any]) -> str:
    if value in {"G1", "G4"}:
        return value
    group = str(manifest.get("group", "G1"))
    return group if group in {"G1", "G4"} else "G1"


def _model_index(config: dict[str, Any], provider_group: str) -> dict[str, dict[str, str]]:
    group = (config.get("groups") or {}).get(provider_group, {})
    return {
        str(row["model_id"]): {"key_file": str(row["key_file"])}
        for row in group.get("models") or []
    }


def _cost(result: dict[str, Any]) -> float:
    used = (((result.get("metadata") or {}).get("budget") or {}).get("used") or {})
    try:
        return max(0.0, float(used.get("cost_usd", 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _prior_cost(run_dir: Path, model_id: str) -> float:
    total = 0.0
    locations = [
        run_dir / "models" / model_id,
        run_dir / "timeout_recovery" / "models" / model_id,
        run_dir / "format_recovery" / "models" / model_id,
    ]
    for directory in locations:
        for path in directory.glob("*.json") if directory.exists() else []:
            try:
                total += _cost(_load(path))
            except (OSError, json.JSONDecodeError):
                continue
    return total


def _recovery_candidates(run_dir: Path, model_id: str, mode: str, task_id: str) -> list[Path]:
    prefix = f"{mode}__{task_id.replace(':', '__')}__"
    return sorted((run_dir / "format_recovery" / "models" / model_id).glob(f"{prefix}*.json"))


def _manifest_for(run_dir: Path) -> dict[str, Any]:
    return _load(run_dir / "run_manifest.json")


def _price(manifest: dict[str, Any], direct_key: str, accounting_key: str, default: float) -> float:
    value = manifest.get(direct_key)
    if value is None:
        accounting = manifest.get("accounting_price_proxy_usd_per_1k_tokens")
        if isinstance(accounting, dict):
            value = accounting.get(accounting_key)
        elif accounting is not None:
            value = accounting
    try:
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def _plan_rows(organized_dir: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    source = organized_dir / "format_failures" / "selected_format_failures.jsonl"
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            run_dir = Path(row["run_dir"])
            manifest = _manifest_for(run_dir)
            provider_group = str(row["provider_group"])
            model_id = str(row["model_id"])
            mode = _mode(str(row["mode"]), manifest)
            model_index = _model_index(config, provider_group)
            if model_id not in model_index:
                raise ValueError(f"{provider_group}: model missing from config: {model_id}")
            candidates = _recovery_candidates(run_dir, model_id, mode, str(row["task_id"]))
            rows.append(
                {
                    "run_dir": str(run_dir),
                    "run_id": str(manifest.get("run_id", run_dir.name)),
                    "provider_group": provider_group,
                    "model_id": model_id,
                    "key_dir_name": str((config.get("groups") or {}).get(provider_group, {}).get("key_dir") or provider_group),
                    "key_file": model_index[model_id]["key_file"],
                    "mode": mode,
                    "level": int(manifest.get("difficulty_level", row.get("difficulty_level") or 1)),
                    "task_id": str(row["task_id"]),
                    "raw_result_path": str(row["raw_result_path"]),
                    "previous_selected_result_path": str(row["selected_result_path"]),
                    "existing_recovery_results": [str(path) for path in candidates],
                    "already_recovered": bool(candidates),
                    "base_url": str(manifest.get("base_url", config.get("base_url", "https://token.ctflow.cn/v1"))),
                    "max_cost_usd_per_model": float(manifest.get("max_cost_usd_per_model", manifest.get("per_model_budget_usd", 200.0))),
                    "max_output_tokens": int(manifest.get("max_output_tokens", 2048)),
                    "input_price_usd_per_1k_proxy": _price(manifest, "input_price_usd_per_1k_proxy", "input", 0.001),
                    "output_price_usd_per_1k_proxy": _price(manifest, "output_price_usd_per_1k_proxy", "output", 0.003),
                }
            )
    return rows


def _run_one(task: dict[str, Any], *, key_root: Path, data_dir: Path, timeout_seconds: float, per_task_cap: float) -> dict[str, Any]:
    key_path = key_root / task["key_dir_name"] / task["key_file"]
    key = key_path.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise RuntimeError(f"invalid local key format for {task['provider_group']}/{task['key_file']}")
    output_dir = Path(task["run_dir"]) / "format_recovery" / "models" / task["model_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = OpenAICompatibleProvider(
        api_key=key,
        base_url=task["base_url"],
        model_name=task["model_id"],
        timeout=timeout_seconds,
        max_retries=0,
        input_cost_per_1k=task["input_price_usd_per_1k_proxy"],
        output_cost_per_1k=task["output_price_usd_per_1k_proxy"],
        max_cost_usd=per_task_cap,
        max_output_tokens=task["max_output_tokens"],
    )
    result = run_task(
        task["task_id"],
        provider,
        task["mode"],
        data_dir=data_dir,
        output_dir=output_dir,
        max_calls=1,
        group=task["mode"],
    )
    validation = result.get("validation") or {}
    return {
        "task_id": task["task_id"],
        "model_id": task["model_id"],
        "run_id": task["run_id"],
        "run_dir": task["run_dir"],
        "status": result.get("status"),
        "validation_status": validation.get("status"),
        "answer_correct": bool(validation.get("answer_correct", False)),
        "protocol_valid": result.get("protocol_valid"),
        "result_directory": str(output_dir),
        "recovered_timeout": _is_transport_timeout(result),
        "cost_usd": _cost(result),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--organized-dir", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--key-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = _load(args.model_config.resolve())
    tasks = _plan_rows(args.organized_dir.resolve(), config)
    pending = [task for task in tasks if not task["already_recovered"]]
    by_run: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        by_run.setdefault(task["run_dir"], []).append(task)
    timestamp = datetime.now(timezone.utc).isoformat()
    for run_dir, run_tasks in by_run.items():
        recovery_dir = Path(run_dir) / "format_recovery"
        recovery_dir.mkdir(parents=True, exist_ok=True)
        plan = {
            "generated_at_utc": timestamp,
            "recovery_type": "format_failure_retry",
            "run_dir": run_dir,
            "run_id": run_tasks[0]["run_id"],
            "task_count": len(run_tasks),
            "pending_count": sum(not task["already_recovered"] for task in run_tasks),
            "tasks": run_tasks,
        }
        (recovery_dir / "format_recovery_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tasks": len(tasks), "pending": len(pending), "dry_run": args.dry_run}, ensure_ascii=False), flush=True)
    if args.dry_run or not pending:
        return 0

    results: list[dict[str, Any]] = []

    def submit(task: dict[str, Any]) -> dict[str, Any]:
        siblings = [item for item in pending if item["run_dir"] == task["run_dir"] and item["model_id"] == task["model_id"]]
        previous = _prior_cost(Path(task["run_dir"]), task["model_id"])
        remaining = max(0.000001, task["max_cost_usd_per_model"] - previous)
        cap = remaining / max(1, len(siblings))
        return _run_one(task, key_root=args.key_root.resolve(), data_dir=args.data_dir.resolve(), timeout_seconds=args.timeout_seconds, per_task_cap=cap)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {executor.submit(submit, task): task for task in pending}
        for future in as_completed(futures):
            task = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {
                    "task_id": task["task_id"],
                    "model_id": task["model_id"],
                    "run_id": task["run_id"],
                    "run_dir": task["run_dir"],
                    "status": "RETRY_PROCESS_ERROR",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        grouped.setdefault(row["run_dir"], []).append(row)
    for run_dir, run_tasks in by_run.items():
        recovery_dir = Path(run_dir) / "format_recovery"
        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "recovery_type": "format_failure_retry",
            "run_id": run_tasks[0]["run_id"],
            "task_count": len(run_tasks),
            "retried_count": len(grouped.get(run_dir, [])),
            "results": grouped.get(run_dir, []),
        }
        (recovery_dir / "format_recovery_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
