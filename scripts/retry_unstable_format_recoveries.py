#!/usr/bin/env python3
"""Second attempt only for format-recovery requests that timed out or hit 429."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from scientific_discovery.models.provider import OpenAICompatibleProvider
from scientific_discovery.theory_benchmark.runner import run_task

from retry_format_failures import _cost, _load, _mode, _model_index, _price, _prior_cost
from retry_timeout_tasks import _is_transport_timeout


def _transient_429(result_path: Path) -> bool:
    try:
        result = _load(result_path)
    except (OSError, json.JSONDecodeError):
        return False
    for trace in ((result.get("metadata") or {}).get("provider_trace") or []):
        error = trace.get("error") if isinstance(trace, dict) else None
        if isinstance(error, dict) and "429" in str(error.get("message", "")):
            return True
    return False


def _candidates(run_dir: Path, model_id: str, mode: str, task_id: str, stage: str) -> list[Path]:
    prefix = f"{mode}__{task_id.replace(':', '__')}__"
    return sorted((run_dir / stage / "models" / model_id).glob(f"{prefix}*.json"))


def _run_one(task: dict[str, Any], *, key_root: Path, data_dir: Path, timeout_seconds: float, per_task_cap: float, stage: str) -> dict[str, Any]:
    key_path = key_root / task["key_dir_name"] / task["key_file"]
    key = key_path.read_text(encoding="utf-8").strip()
    output_dir = Path(task["run_dir"]) / stage / "models" / task["model_id"]
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
    result = run_task(task["task_id"], provider, task["mode"], data_dir=data_dir, output_dir=output_dir, max_calls=1, group=task["mode"])
    return {
        "task_id": task["task_id"],
        "model_id": task["model_id"],
        "run_id": task["run_id"],
        "run_dir": task["run_dir"],
        "status": result.get("status"),
        "validation_status": (result.get("validation") or {}).get("status"),
        "answer_correct": bool((result.get("validation") or {}).get("answer_correct", False)),
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
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    parser.add_argument("--selection", choices=("unstable", "remaining_format"), default="unstable")
    parser.add_argument("--output-stage", default="format_recovery_retry2")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    organized = args.organized_dir.resolve()
    config = _load(args.model_config.resolve())
    selected_path = organized / "format_failures" / "selected_format_failures.jsonl"
    recovery_path = organized / "format_failures" / "format_recovery_results.jsonl"
    selected = {}
    for line in selected_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            selected[(str(Path(row["run_dir"])), str(row["model_id"]), str(row["task_id"]))] = row

    tasks: list[dict[str, Any]] = []
    for line in recovery_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        retry_row = json.loads(line)
        if args.selection == "unstable":
            if retry_row["recovery_classification"] not in {"transport_timeout", "provider_error"}:
                continue
        elif not retry_row["recovery_classification"].startswith("format_"):
            continue
        result_path = Path(retry_row["format_recovery_result_path"])
        if args.selection == "unstable" and retry_row["recovery_classification"] == "provider_error" and not _transient_429(result_path):
            continue
        key = (str(Path(retry_row["run_dir"])), str(retry_row["model_id"]), str(retry_row["task_id"]))
        row = selected[key]
        run_dir = Path(row["run_dir"])
        manifest = _load(run_dir / "run_manifest.json")
        provider_group = str(row["provider_group"])
        model_id = str(row["model_id"])
        mode = _mode(str(row["mode"]), manifest)
        model_index = _model_index(config, provider_group)
        tasks.append({
            "run_dir": str(run_dir),
            "run_id": str(manifest.get("run_id", run_dir.name)),
            "provider_group": provider_group,
            "model_id": model_id,
            "key_dir_name": str((config.get("groups") or {}).get(provider_group, {}).get("key_dir") or provider_group),
            "key_file": model_index[model_id]["key_file"],
            "mode": mode,
            "task_id": str(row["task_id"]),
            "base_url": str(manifest.get("base_url", config.get("base_url", "https://token.ctflow.cn/v1"))),
            "max_cost_usd_per_model": float(manifest.get("max_cost_usd_per_model", manifest.get("per_model_budget_usd", 200.0))),
            "max_output_tokens": int(manifest.get("max_output_tokens", 2048)),
            "input_price_usd_per_1k_proxy": _price(manifest, "input_price_usd_per_1k_proxy", "input", 0.001),
            "output_price_usd_per_1k_proxy": _price(manifest, "output_price_usd_per_1k_proxy", "output", 0.003),
            "existing_retry2": [str(path) for path in _candidates(run_dir, model_id, mode, str(row["task_id"]), args.output_stage)],
        })
    pending = [task for task in tasks if not task["existing_retry2"]]
    timestamp = datetime.now(timezone.utc).isoformat()
    by_run: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        by_run.setdefault(task["run_dir"], []).append(task)
    for run_dir, run_tasks in by_run.items():
        directory = Path(run_dir) / args.output_stage
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{args.output_stage}_plan.json").write_text(json.dumps({
            "generated_at_utc": timestamp,
            "recovery_type": f"format_failure_{args.selection}_{args.output_stage}",
            "run_id": run_tasks[0]["run_id"],
            "task_count": len(run_tasks),
            "pending_count": sum(not task["existing_retry2"] for task in run_tasks),
            "tasks": run_tasks,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tasks": len(tasks), "pending": len(pending), "dry_run": args.dry_run}, ensure_ascii=False), flush=True)
    if args.dry_run or not pending:
        return 0

    results: list[dict[str, Any]] = []
    def submit(task: dict[str, Any]) -> dict[str, Any]:
        siblings = [item for item in pending if item["run_dir"] == task["run_dir"] and item["model_id"] == task["model_id"]]
        previous = _prior_cost(Path(task["run_dir"]), task["model_id"])
        retry_cost = sum(_cost(_load(path)) for path in (Path(task["run_dir"]) / args.output_stage / "models" / task["model_id"]).glob("*.json")) if (Path(task["run_dir"]) / args.output_stage / "models" / task["model_id"]).exists() else 0.0
        remaining = max(0.000001, task["max_cost_usd_per_model"] - previous - retry_cost)
        return _run_one(task, key_root=args.key_root.resolve(), data_dir=args.data_dir.resolve(), timeout_seconds=args.timeout_seconds, per_task_cap=remaining / max(1, len(siblings)), stage=args.output_stage)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {executor.submit(submit, task): task for task in pending}
        for future in as_completed(futures):
            task = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {"task_id": task["task_id"], "model_id": task["model_id"], "run_id": task["run_id"], "run_dir": task["run_dir"], "status": "RETRY_PROCESS_ERROR", "error_type": type(exc).__name__, "error": str(exc)}
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        grouped.setdefault(row["run_dir"], []).append(row)
    for run_dir, run_tasks in by_run.items():
        directory = Path(run_dir) / args.output_stage
        (directory / f"{args.output_stage}_summary.json").write_text(json.dumps({
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "recovery_type": f"format_failure_{args.selection}_{args.output_stage}",
            "run_id": run_tasks[0]["run_id"],
            "task_count": len(run_tasks),
            "retried_count": len(grouped.get(run_dir, [])),
            "results": grouped.get(run_dir, []),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
