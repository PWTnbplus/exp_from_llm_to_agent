#!/usr/bin/env python3
"""Retry only recorded transport-timeout tasks from completed CTFlow runs.

The original result files are never overwritten.  Recovery results and their
traces are written below each run's ``timeout_recovery`` directory so that the
raw benchmark remains auditable and the recovered view can be built separately.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any

from scientific_discovery.models.provider import OpenAICompatibleProvider
from scientific_discovery.theory_benchmark.runner import run_task


TIMEOUT_RE = re.compile(
    r"(?i)(timeout|timed out|time out|deadline exceeded|deadline reached|"
    r"read timed out|connect timed out|request timed out|响应超时|超时)"
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_transport_timeout(result: dict[str, Any]) -> bool:
    metadata = result.get("metadata") or {}
    for trace in metadata.get("provider_trace") or []:
        error = trace.get("error") or {}
        if str(error.get("type", "")).lower() in {"timeouterror", "timeout"}:
            return True
        if TIMEOUT_RE.search(str(error.get("message", ""))):
            return True
    answer = result.get("answer")
    return isinstance(answer, dict) and bool(TIMEOUT_RE.search(str(answer.get("error", ""))))


def _result_candidates(model_dir: Path, mode: str, task_id: str) -> list[Path]:
    prefix = f"{mode}__{task_id.replace(':', '__')}__"
    return sorted(model_dir.glob(f"{prefix}*.json"))


def _recovery_candidates(model_dir: Path, mode: str, task_id: str) -> list[Path]:
    prefix = f"{mode}__{task_id.replace(':', '__')}__"
    return sorted(model_dir.glob(f"{prefix}*.json"))


def _model_index(config: dict[str, Any], provider_group: str) -> dict[str, dict[str, str]]:
    rows = (config.get("groups") or {}).get(provider_group, {}).get("models") or []
    return {str(row["model_id"]): {"key_file": str(row["key_file"])} for row in rows}


def _runs(root: Path, selected: list[Path] | None, include_limited: bool = False) -> list[Path]:
    if selected:
        return [p.resolve() for p in selected]
    return sorted(
        manifest.parent.resolve()
        for manifest in root.rglob("run_manifest.json")
        if include_limited or any("_without_lim" in part for part in manifest.parts)
    )


def collect_plan(run_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    manifest = _load_json(run_dir / "run_manifest.json")
    timeout_report = _load_json(run_dir / "timeout_check.json")
    # Older DeepSeek unlimited manifests predate ``provider_group``; the
    # directory name is still part of the immutable run layout.
    provider_group = str(
        manifest.get("provider_group")
        or run_dir.parts[-3].removesuffix("_without_lim")
    )
    group_config = (config.get("groups") or {}).get(provider_group, {})
    key_dir_name = str(group_config.get("key_dir") or provider_group)
    model_index = _model_index(config, provider_group)
    raw_mode = str(manifest.get("mode", ""))
    mode = raw_mode if raw_mode in {"G1", "G4"} else str(manifest.get("group", raw_mode))
    tasks: list[dict[str, Any]] = []
    skipped_non_timeout = 0
    report_rows_by_model: dict[str, dict[str, Any]] = {}
    for model_row in timeout_report.get("models") or []:
        raw_model_id = model_row.get("model_id")
        if isinstance(raw_model_id, dict):
            raw_model_id = raw_model_id.get("model_id")
        if raw_model_id:
            report_rows_by_model[str(raw_model_id)] = model_row
    # Discover model directories directly because some legacy timeout reports
    # serialized a model configuration dict as a string and therefore listed
    # zero files even though the raw results are present.
    model_dirs = sorted(path for path in (run_dir / "models").iterdir() if path.is_dir())
    for model_dir in model_dirs:
        model_id = model_dir.name
        model_row = report_rows_by_model.get(model_id, {})
        # The historical timeout checker could miss a timeout when a model
        # response JSON contained case-variant duplicate keys.  Re-scan every
        # raw result with Python's JSON parser and take the union.
        timeout_task_ids = {str(task_id) for task_id in (model_row.get("timeout_task_ids") or [])}
        for candidate in model_dir.glob("*.json"):
            try:
                candidate_result = _load_json(candidate)
            except (OSError, json.JSONDecodeError):
                continue
            if _is_transport_timeout(candidate_result) and candidate_result.get("task_id"):
                timeout_task_ids.add(str(candidate_result["task_id"]))
        for task_id in sorted(timeout_task_ids):
            original = _result_candidates(model_dir, mode, str(task_id))
            transport_timeout = False
            original_path = None
            for path in original:
                try:
                    data = _load_json(path)
                except (OSError, json.JSONDecodeError):
                    continue
                if _is_transport_timeout(data):
                    transport_timeout = True
                    original_path = str(path)
                    break
            if not transport_timeout:
                skipped_non_timeout += 1
                continue
            if model_id not in model_index:
                raise ValueError(f"{provider_group}: model missing from config: {model_id}")
            recovery_dir = run_dir / "timeout_recovery" / "models" / model_id
            recovered = _recovery_candidates(recovery_dir, mode, str(task_id))
            tasks.append(
                {
                    "run_dir": str(run_dir),
                    "run_id": str(manifest["run_id"]),
                    "provider_group": provider_group,
                    "mode": mode,
                    "level": int(manifest["difficulty_level"]),
                    "model_id": model_id,
                    "key_dir_name": key_dir_name,
                    "key_file": model_index[model_id]["key_file"],
                    "task_id": str(task_id),
                    "original_result": original_path,
                    "recovered_results": [str(p) for p in recovered],
                    "already_recovered": bool(recovered),
                }
            )
    return {
        "run_id": manifest["run_id"],
        "run_dir": str(run_dir),
        "provider_group": provider_group,
        "mode": mode,
        "level": int(manifest["difficulty_level"]),
        "base_url": manifest.get("base_url", config.get("base_url", "https://token.ctflow.cn/v1")),
        "key_directory": manifest.get("local_key_directory"),
        "key_dir_name": key_dir_name,
        "max_cost_usd_per_model": float(manifest.get("max_cost_usd_per_model", manifest.get("per_model_budget_usd", 200.0))),
        "max_output_tokens": int(manifest.get("max_output_tokens", 2048)),
        "input_price_usd_per_1k_proxy": float(manifest.get("input_price_usd_per_1k_proxy", 0.001)),
        "output_price_usd_per_1k_proxy": float(manifest.get("output_price_usd_per_1k_proxy", 0.003)),
        "tasks": tasks,
        "skipped_non_timeout": skipped_non_timeout,
    }


def _existing_cost(task: dict[str, Any]) -> float:
    total = 0.0
    paths = [task.get("original_result")] + list(task.get("recovered_results") or [])
    for raw_path in paths:
        if not raw_path:
            continue
        try:
            data = _load_json(Path(raw_path))
            total += max(0.0, float(((data.get("metadata") or {}).get("budget") or {}).get("used", {}).get("cost_usd", 0.0)))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return total


def _run_one(
    task: dict[str, Any],
    *,
    key_root: Path,
    data_dir: Path,
    base_url: str,
    timeout_seconds: float,
    max_output_tokens: int,
    input_price: float,
    output_price: float,
    per_task_cap: float,
) -> dict[str, Any]:
    key_path = key_root / task["key_dir_name"] / task["key_file"]
    key = key_path.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise RuntimeError(f"invalid local key format for {task['provider_group']}/{task['key_file']}")
    output_dir = Path(task["run_dir"]) / "timeout_recovery" / "models" / task["model_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = OpenAICompatibleProvider(
        api_key=key,
        base_url=base_url,
        model_name=task["model_id"],
        timeout=timeout_seconds,
        max_retries=0,
        input_cost_per_1k=input_price,
        output_cost_per_1k=output_price,
        max_cost_usd=per_task_cap,
        max_output_tokens=max_output_tokens,
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
    return {
        "task_id": task["task_id"],
        "model_id": task["model_id"],
        "run_id": task["run_id"],
        "run_dir": task["run_dir"],
        "status": result.get("status"),
        "validation_status": (result.get("validation") or {}).get("status"),
        "answer_correct": bool((result.get("validation") or {}).get("answer_correct", False)),
        "result_directory": str(output_dir),
        "recovered_timeout": _is_transport_timeout(result),
        "cost_usd": float((((result.get("metadata") or {}).get("budget") or {}).get("used") or {}).get("cost_usd", 0.0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--key-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, action="append")
    parser.add_argument("--include-limited", action="store_true", help="also discover legacy limited-budget runs")
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_workers <= 0:
        raise SystemExit("--max-workers must be positive")
    config = _load_json(args.model_config.resolve())
    plans = [collect_plan(run, config) for run in _runs(args.benchmark_root.resolve(), args.run_dir, args.include_limited)]
    timestamp = datetime.now(timezone.utc).isoformat()
    all_tasks = [task for plan in plans for task in plan["tasks"] if not task["already_recovered"]]
    for plan in plans:
        recovery_dir = Path(plan["run_dir"]) / "timeout_recovery"
        recovery_dir.mkdir(parents=True, exist_ok=True)
        plan["generated_at_utc"] = timestamp
        plan["task_count"] = len(plan["tasks"])
        plan["pending_count"] = sum(not task["already_recovered"] for task in plan["tasks"])
        (recovery_dir / "timeout_recovery_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(plans), "timeout_tasks": len(all_tasks), "dry_run": args.dry_run}, ensure_ascii=False), flush=True)
    if args.dry_run or not all_tasks:
        return 0

    # Allocate the remaining local proxy ceiling conservatively per task and
    # keep each model/run independent.  The original raw results are never
    # counted as recovered attempts and are not overwritten.
    results: list[dict[str, Any]] = []
    def submit(task: dict[str, Any]) -> dict[str, Any]:
        plan = next(p for p in plans if p["run_id"] == task["run_id"] and p["run_dir"] == task["run_dir"])
        siblings = [x for x in all_tasks if x["run_id"] == task["run_id"] and x["model_id"] == task["model_id"]]
        previous_cost = sum(_existing_cost(x) for x in siblings)
        remaining = max(0.000001, plan["max_cost_usd_per_model"] - previous_cost)
        cap = remaining / max(1, len(siblings))
        return _run_one(
            task,
            key_root=args.key_root.resolve(),
            data_dir=args.data_dir.resolve(),
            base_url=plan["base_url"],
            timeout_seconds=args.timeout_seconds,
            max_output_tokens=plan["max_output_tokens"],
            input_price=plan["input_price_usd_per_1k_proxy"],
            output_price=plan["output_price_usd_per_1k_proxy"],
            per_task_cap=cap,
        )

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {executor.submit(submit, task): task for task in all_tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                row = future.result()
            except Exception as exc:  # retain failure evidence without stopping other models
                row = {"task_id": task["task_id"], "model_id": task["model_id"], "run_id": task["run_id"], "run_dir": task["run_dir"], "status": "RETRY_PROCESS_ERROR", "error_type": type(exc).__name__, "error": str(exc)}
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        # run_id values are reused across matched LLM/Agent runs and across
        # difficulty levels.  The absolute run directory is the unique key.
        grouped.setdefault(row["run_dir"], []).append(row)
    for plan in plans:
        recovery_dir = Path(plan["run_dir"]) / "timeout_recovery"
        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_id": plan["run_id"],
            "task_count": len(plan["tasks"]),
            "retried_count": len(grouped.get(plan["run_id"], [])),
            "results": grouped.get(plan["run_dir"], []),
        }
        (recovery_dir / "timeout_recovery_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
