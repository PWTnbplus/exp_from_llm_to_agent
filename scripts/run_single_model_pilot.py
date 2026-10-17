#!/usr/bin/env python3
"""Run the frozen NewtonBench pilot for one exact model.

This runner is deliberately bounded-concurrent and checkpointed.  It fills the
frozen pilot repeat design for both matched arms without changing the
scientific orchestration in ``run_one``.  Every registered task-run receives
its own directory, result artifact, trace, and row in the secret-free pilot
contract; provider or parser failures remain in the denominator.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_matrix_scientific import (  # noqa: E402
    DEFAULT_INPUT_RATE,
    DEFAULT_MAX_API_CALLS,
    DEFAULT_MAX_INPUT_TOKENS,
    DEFAULT_MAX_OUTPUT_BUDGET,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_PROVIDER_TIMEOUT_SECONDS,
    RESERVATION_OUTPUT_MULTIPLIER,
    load_tasks,
    provider_trace_summary,
    safe_slug,
    write_json,
)
from src.scientific_discovery.benchmark.base import TaskSpec  # noqa: E402
from src.scientific_discovery.cli import _generic_engineering_provider  # noqa: E402
from src.scientific_discovery.environment.budget import BudgetLimits  # noqa: E402
from src.scientific_discovery.experiment.runner import run_one  # noqa: E402
from src.scientific_discovery.models.provider import OpenAICompatibleProvider  # noqa: E402


RUNNERS = ("llm_only", "agent")


def _provider(args: argparse.Namespace, task_cap: float, task: TaskSpec, runner: str):
    if args.provider == "mock":
        return _generic_engineering_provider(
            task, ROOT / "third_party" / "NewtonBench", runner
        )
    key = os.getenv("CTFLOW_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = os.getenv("CTFLOW_BASE_URL") or os.getenv("LLM_BASE_URL")
    if not key or not base_url:
        raise RuntimeError("CTFLOW_API_KEY/LLM_API_KEY and CTFLOW_BASE_URL/LLM_BASE_URL are required")
    return OpenAICompatibleProvider(
        api_key=key,
        base_url=base_url,
        model_name=args.model,
        timeout=args.provider_timeout_seconds,
        max_retries=0,
        input_cost_per_1k=args.input_cost_per_1k,
        output_cost_per_1k=args.output_cost_per_1k,
        max_cost_usd=task_cap,
        max_output_tokens=args.max_output_tokens,
        reservation_output_tokens=args.max_output_tokens * RESERVATION_OUTPUT_MULTIPLIER,
    )


def _row_base(task: TaskSpec, runner: str, replicate: int, task_cap: float, path: Path) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "runner": runner,
        "runner_name": "single_agent" if runner == "agent" else "llm_only",
        "replicate_index": replicate,
        "task_cap_usd": task_cap,
        "output_dir": str(path),
    }


def _write_checkpoint(output: Path, metadata: dict[str, Any], rows: list[dict[str, Any]], *, final: bool = False) -> None:
    actual = sum(float(row.get("cost_usd", 0.0) or 0.0) for row in rows)
    reserved = sum(float(row.get("reserved_cost_usd", 0.0) or 0.0) for row in rows)
    registered = int(metadata["expected_runs"])
    budget_ok = reserved <= metadata["max_cost_usd"] + 1e-9 and actual <= metadata["max_cost_usd"] + 1e-9
    complete = len(rows) == registered
    failures = any(row.get("status") != "completed" for row in rows)
    payload = {
        "schema_version": 1,
        "status": "COMPLETED" if final and complete and not failures and budget_ok
        else ("COMPLETED_WITH_TASK_FAILURES" if final and complete and budget_ok else ("FAILED_BUDGET" if final and complete else "IN_PROGRESS")),
        "execution_complete": complete,
        "scientific_release_allowed": False,
        "model_id": metadata["model_id"],
        "runner_scope": list(RUNNERS),
        "provider": metadata["provider"],
        "base_url": metadata["base_url"],
        "provider_billing_verified": False,
        "cost_interpretation": "local_proxy_unverified_provider_billing",
        "budget_enforced": budget_ok,
        "max_cost_usd": metadata["max_cost_usd"],
        "actual_cost_usd": actual,
        "reserved_cost_usd": reserved,
        "manifest": metadata["manifest"],
        "manifest_sha256": metadata["manifest_sha256"],
        "design": "pilot",
        "task_count": metadata["task_count"],
        "repeats_per_task_per_arm": metadata["repeats"],
        "expected_runs": registered,
        "registered_runs": len(rows),
        "task_failures": sum(row.get("status") != "completed" for row in rows),
        "validated_success_count": sum(bool(row.get("validated_success")) for row in rows),
        "rows": rows,
    }
    write_json(output / "result.json", payload)


def _execute_task_run(
    args: argparse.Namespace,
    task: TaskSpec,
    runner: str,
    replicate: int,
    index: int,
    task_cap: float,
    output: Path,
    upstream: Path,
    manifest_hash: str,
) -> dict[str, Any]:
    task_dir = output / f"replicate-{replicate:03d}" / runner / f"{index:03d}_{safe_slug(task.task_id)}"
    task_dir.mkdir(parents=True, exist_ok=True)
    row = _row_base(task, runner, replicate, task_cap, task_dir.relative_to(output))
    provider = None
    try:
        provider = _provider(args, task_cap, task, runner)
        result, validation = run_one(
            task=task,
            repo_root=upstream,
            provider=provider,
            runner_name="single_agent" if runner == "agent" else "llm_only",
            limits=BudgetLimits(
                max_experiments=args.max_experiments,
                max_api_calls=DEFAULT_MAX_API_CALLS,
                max_input_tokens=DEFAULT_MAX_INPUT_TOKENS,
                max_output_tokens=DEFAULT_MAX_OUTPUT_BUDGET,
                max_cost_usd=task_cap,
                max_runtime_seconds=args.timeout_seconds,
            ),
            output_dir=task_dir,
            replicate_index=replicate,
            design="pilot",
            manifest_sha256=manifest_hash,
        )
        policy = result.metadata.get("policy", {}) if isinstance(result.metadata, dict) else {}
        violations = list(policy.get("violations", [])) if isinstance(policy, dict) else []
        trace = provider_trace_summary(provider)
        row.update({
            "status": result.status,
            "validation_status": validation.get("status"),
            "validated_success": bool(validation.get("validated_success", False)),
            "protocol_valid": result.status == "completed" and not violations,
            "evaluator_valid": validation.get("status") != "VALIDATOR_ERROR",
            "policy_violations": violations,
            **trace,
        })
    except Exception as exc:
        trace = provider_trace_summary(provider) if provider is not None else {
            "provider_attempts": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "reserved_cost_usd": 0.0,
        }
        row.update({
            "status": "failed",
            "validation_status": "NOT_RUN",
            "validated_success": False,
            "protocol_valid": False,
            "evaluator_valid": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:1000],
            **trace,
        })
        write_json(task_dir / "task_failure.json", {
            "task_id": task.task_id,
            "runner": runner,
            "replicate_index": replicate,
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:1000],
            "provider_attempts": trace["provider_attempts"],
            "reserved_cost_usd": trace["reserved_cost_usd"],
        })
    return row


def run_pilot(args: argparse.Namespace) -> dict[str, Any]:
    if args.provider == "ctflow" and not args.allow_paid:
        raise ValueError("real provider runs require --allow-paid")
    if args.max_cost_usd <= 0:
        raise ValueError("max_cost_usd must be positive")
    if args.repeats < 1 or args.max_experiments < 1 or args.max_parallel < 1:
        raise ValueError("repeats, max_experiments, and max_parallel must be positive")
    tasks, manifest_hash = load_tasks(args.manifest.resolve())
    if args.limit_tasks:
        tasks = tasks[: args.limit_tasks]
    if not tasks:
        raise ValueError("no tasks selected")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    upstream = (ROOT / "third_party" / "NewtonBench").resolve()
    if not upstream.is_dir():
        raise FileNotFoundError(f"pinned NewtonBench checkout missing: {upstream}")
    expected = len(tasks) * args.repeats * len(RUNNERS)
    metadata = {
        "model_id": args.model,
        "provider": args.provider,
        "base_url": os.getenv("CTFLOW_BASE_URL") or os.getenv("LLM_BASE_URL") or "mock",
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": manifest_hash,
        "max_cost_usd": float(args.max_cost_usd),
        "task_count": len(tasks),
        "repeats": args.repeats,
        "expected_runs": expected,
        "max_parallel": args.max_parallel,
    }
    rows: list[dict[str, Any]] = []
    checkpoint = output / "result.json"
    if args.resume and checkpoint.is_file():
        prior = json.loads(checkpoint.read_text(encoding="utf-8"))
        if prior.get("model_id") != args.model or prior.get("manifest_sha256") != manifest_hash:
            raise ValueError("resume checkpoint does not match model or frozen manifest")
        if prior.get("expected_runs") != expected:
            raise ValueError("resume checkpoint does not match expected run count")
        rows = prior.get("rows") or []
        if not isinstance(rows, list):
            raise ValueError("resume checkpoint rows must be a list")
    write_json(output / "manifest.json", {**metadata, "design": "pilot", "runner_scope": list(RUNNERS), "resumed_rows": len(rows)})
    completed_keys = {(row.get("replicate_index"), row.get("runner"), row.get("task_id")) for row in rows}
    remaining_reserved = float(args.max_cost_usd) - sum(float(row.get("reserved_cost_usd", 0.0) or 0.0) for row in rows)
    pending: list[tuple[int, int, TaskSpec, str]] = []
    for replicate in range(args.repeats):
        for index, task in enumerate(tasks):
            for runner in RUNNERS:
                key = (replicate, runner, task.task_id)
                if key not in completed_keys:
                    pending.append((replicate, index, task, runner))
    if pending:
        task_cap = remaining_reserved / len(pending)
        if not math.isfinite(task_cap) or task_cap <= 0:
            raise RuntimeError("aggregate local reservation exhausted")
        with ThreadPoolExecutor(max_workers=min(args.max_parallel, len(pending))) as pool:
            futures = {
                pool.submit(_execute_task_run, args, task, runner, replicate, index, task_cap, output, upstream, manifest_hash):
                (replicate, runner, task.task_id)
                for replicate, index, task, runner in pending
            }
            for future in as_completed(futures):
                row = future.result()
                rows.append(row)
                completed_keys.add((row["replicate_index"], row["runner"], row["task_id"]))
                remaining_reserved -= float(row.get("reserved_cost_usd", 0.0) or 0.0)
                if remaining_reserved < -1e-9:
                    raise RuntimeError("aggregate local reservation exceeded")
                _write_checkpoint(output, metadata, rows)
    _write_checkpoint(output, metadata, rows, final=True)
    return json.loads((output / "result.json").read_text(encoding="utf-8"))


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--max-experiments", type=int, default=6)
    ap.add_argument("--provider", choices=("ctflow", "mock"), default="ctflow")
    ap.add_argument("--allow-paid", action="store_true")
    ap.add_argument("--max-cost-usd", type=float, required=True)
    ap.add_argument("--input-cost-per-1k", type=float, default=DEFAULT_INPUT_RATE)
    ap.add_argument("--output-cost-per-1k", type=float, default=0.003)
    ap.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    ap.add_argument("--timeout-seconds", type=float, default=3_600.0)
    ap.add_argument("--provider-timeout-seconds", type=float, default=DEFAULT_PROVIDER_TIMEOUT_SECONDS)
    ap.add_argument("--max-parallel", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = run_pilot(args)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": result["status"],
        "model_id": result["model_id"],
        "expected_runs": result["expected_runs"],
        "registered_runs": result["registered_runs"],
        "task_failures": result["task_failures"],
        "actual_cost_usd": result["actual_cost_usd"],
        "reserved_cost_usd": result["reserved_cost_usd"],
        "result": str(args.output.resolve() / "result.json"),
    }, ensure_ascii=False))
    return 0 if result["status"] == "COMPLETED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
