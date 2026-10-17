#!/usr/bin/env python3
"""Run one real CTFlow model/arm over the frozen NewtonBench manifest.

This is the project-specific adapter required by ``scripts/model_matrix.py``.
It intentionally delegates all scientific behavior to the existing
``run_one`` orchestration so the LLM-only frozen-plan and single-Agent policy
remain the source of truth.  The adapter adds only matrix concerns:

* exact model/base URL selection from the host environment;
* per-task allocation of a conservative local cost reservation;
* durable task-level traces and failure records;
* a small, secret-free ``result.json`` contract for the matrix host.

The cost values are local proxy rates.  They bound this runner's reservations
but are not provider billing evidence; the result therefore records that
distinction explicitly and never presents proxy cost as an invoice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scientific_discovery.benchmark.base import TaskSpec
from src.scientific_discovery.cli import _generic_engineering_provider
from src.scientific_discovery.environment.budget import BudgetLimits
from src.scientific_discovery.experiment.runner import run_one
from src.scientific_discovery.models.provider import OpenAICompatibleProvider


DEFAULT_INPUT_RATE = 0.001
DEFAULT_OUTPUT_RATE = 0.003
DEFAULT_MAX_OUTPUT_TOKENS = 2048
RESERVATION_OUTPUT_MULTIPLIER = 8
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 180.0
DEFAULT_MAX_API_CALLS = 20
DEFAULT_MAX_INPUT_TOKENS = 100_000
DEFAULT_MAX_OUTPUT_BUDGET = 30_000
DEFAULT_MAX_RUNTIME_SECONDS = 3_600.0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)[:100] or "task"


def load_tasks(manifest: Path) -> tuple[list[TaskSpec], str]:
    if not manifest.is_file():
        raise FileNotFoundError(f"manifest does not exist: {manifest}")
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("manifest must be a non-empty JSON list")
    tasks = [TaskSpec(**row) for row in raw]
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("manifest contains duplicate task_id values")
    if any(not task.supported for task in tasks):
        raise ValueError("manifest contains unsupported tasks")
    return tasks, sha256_file(manifest)


def provider_trace_summary(provider: Any) -> dict[str, Any]:
    traces = provider.audit_trace()
    actual_cost = 0.0
    input_tokens = 0
    output_tokens = 0
    for item in traces:
        usage = item.get("response", {}).get("usage", {}) if isinstance(item, dict) else {}
        actual_cost += float(usage.get("cost_usd", 0.0) or 0.0)
        input_tokens += int(usage.get("input_tokens", 0) or 0)
        output_tokens += int(usage.get("output_tokens", 0) or 0)
    return {
        "provider_attempts": len(traces),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": actual_cost,
        "reserved_cost_usd": float(getattr(provider, "_reserved_cost_usd", 0.0) or 0.0),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def build_provider(args: argparse.Namespace, task_cap: float):
    if args.provider == "mock":
        # This branch exists only for adapter contract tests and local smoke
        # checks.  Its output is marked mock=True and can never pass the paid
        # matrix acceptance contract.
        runner_name = "single_agent" if args.mode == "agent" else "llm_only"
        return _generic_engineering_provider(
            args._current_task, ROOT / "third_party" / "NewtonBench", runner_name
        )
    key = os.getenv("CTFLOW_API_KEY") or os.getenv("LLM_API_KEY")
    if not key:
        raise RuntimeError("CTFLOW_API_KEY or LLM_API_KEY is not configured")
    base_url = os.getenv("CTFLOW_BASE_URL") or os.getenv("LLM_BASE_URL")
    if not base_url:
        raise RuntimeError("CTFLOW_BASE_URL or LLM_BASE_URL is not configured")
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


def run_matrix_arm(args: argparse.Namespace) -> dict[str, Any]:
    manifest = args.manifest.resolve()
    tasks, manifest_hash = load_tasks(manifest)
    if args.limit_tasks:
        tasks = tasks[: args.limit_tasks]
    if not tasks:
        raise ValueError("no tasks selected")
    if args.max_cost_usd <= 0:
        raise ValueError("max_cost_usd must be positive")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    upstream = (ROOT / "third_party" / "NewtonBench").resolve()
    if not upstream.is_dir():
        raise FileNotFoundError(f"pinned NewtonBench checkout missing: {upstream}")
    runner_name = "single_agent" if args.mode == "agent" else "llm_only"
    remaining_reserved = float(args.max_cost_usd)
    rows: list[dict[str, Any]] = []

    for index, task in enumerate(tasks):
        remaining_tasks = len(tasks) - index
        task_cap = remaining_reserved / remaining_tasks
        if not math.isfinite(task_cap) or task_cap <= 0:
            raise RuntimeError("aggregate local cost reservation exhausted")
        task_dir = output / "tasks" / f"{index:03d}_{safe_slug(task.task_id)}"
        task_dir.mkdir(parents=True, exist_ok=True)
        args._current_task = task
        provider = build_provider(args, task_cap)
        row: dict[str, Any] = {
            "index": index,
            "task_id": task.task_id,
            "runner": args.mode,
            "runner_name": runner_name,
            "task_cap_usd": task_cap,
            "output_dir": str(task_dir.relative_to(output)),
        }
        try:
            result, validation = run_one(
                task=task,
                repo_root=upstream,
                provider=provider,
                runner_name=runner_name,
                limits=BudgetLimits(
                    max_experiments=args.max_experiments,
                    max_api_calls=DEFAULT_MAX_API_CALLS,
                    max_input_tokens=DEFAULT_MAX_INPUT_TOKENS,
                    max_output_tokens=DEFAULT_MAX_OUTPUT_BUDGET,
                    max_cost_usd=task_cap,
                    max_runtime_seconds=args.timeout_seconds,
                ),
                output_dir=task_dir,
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
            trace = provider_trace_summary(provider)
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
                "runner": args.mode,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:1000],
                "provider_attempts": trace["provider_attempts"],
                "reserved_cost_usd": trace["reserved_cost_usd"],
            })
        rows.append(row)
        # Reservation is conservative and is never refunded.  A failed
        # request is therefore still represented in the aggregate ceiling.
        remaining_reserved -= float(row.get("reserved_cost_usd", 0.0) or 0.0)
        if remaining_reserved < -1e-9:
            raise RuntimeError("aggregate local cost reservation exceeded")

    actual_cost = sum(float(row.get("cost_usd", 0.0) or 0.0) for row in rows)
    reserved_cost = sum(float(row.get("reserved_cost_usd", 0.0) or 0.0) for row in rows)
    completed = all(row.get("status") == "completed" for row in rows)
    protocol_valid = all(row.get("protocol_valid") is True for row in rows)
    evaluator_valid = all(row.get("evaluator_valid") is True for row in rows)
    # Both quantities are gates: reservations bound worst-case exposure before
    # a request, while observed local usage must also remain within the same
    # cap.  The latter is not a billing assertion; provider billing remains
    # explicitly unverified in this adapter.
    budget_enforced = (
        reserved_cost <= float(args.max_cost_usd) + 1e-9
        and actual_cost <= float(args.max_cost_usd) + 1e-9
    )
    result = {
        "schema_version": 1,
        "status": "COMPLETED" if completed and protocol_valid and evaluator_valid and budget_enforced else "FAILED",
        "model_id": args.model,
        "runner": args.mode,
        "protocol_valid": protocol_valid,
        "evaluator_valid": evaluator_valid,
        "mock": args.provider == "mock",
        "cost_usd": actual_cost,
        "reserved_cost_usd": reserved_cost,
        "budget_enforced": budget_enforced,
        "budget_scope": "local_conservative_reservation_per_matrix_arm",
        "cost_interpretation": "local_proxy_unverified_provider_billing",
        "provider_billing_verified": False,
        "provider": args.provider,
        "base_url": os.getenv("CTFLOW_BASE_URL") or os.getenv("LLM_BASE_URL") or "mock",
        "manifest": str(manifest),
        "manifest_sha256": manifest_hash,
        "task_count": len(rows),
        "task_failures": sum(row.get("status") != "completed" for row in rows),
        "validated_success_count": sum(bool(row.get("validated_success")) for row in rows),
        "max_experiments_per_task": args.max_experiments,
        "input_cost_per_1k_usd": args.input_cost_per_1k,
        "output_cost_per_1k_usd": args.output_cost_per_1k,
        "max_output_tokens": args.max_output_tokens,
        "reservation_output_multiplier": RESERVATION_OUTPUT_MULTIPLIER,
        "provider_timeout_seconds": args.provider_timeout_seconds,
        "tasks": rows,
    }
    write_json(output / "result.json", result)
    print(json.dumps({
        "status": result["status"],
        "model_id": args.model,
        "runner": args.mode,
        "task_count": len(rows),
        "task_failures": result["task_failures"],
        "cost_usd": actual_cost,
        "reserved_cost_usd": reserved_cost,
        "result": str(output / "result.json"),
    }, ensure_ascii=False))
    return result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("llm_only", "agent"), required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--max-experiments", type=int, default=6)
    ap.add_argument("--provider", choices=("ctflow", "mock"), default="ctflow")
    ap.add_argument("--allow-paid", action="store_true")
    ap.add_argument("--max-cost-usd", type=float, default=None)
    ap.add_argument("--input-cost-per-1k", type=float, default=DEFAULT_INPUT_RATE)
    ap.add_argument("--output-cost-per-1k", type=float, default=DEFAULT_OUTPUT_RATE)
    ap.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--timeout-seconds", type=float, default=DEFAULT_MAX_RUNTIME_SECONDS)
    ap.add_argument("--provider-timeout-seconds", type=float, default=DEFAULT_PROVIDER_TIMEOUT_SECONDS)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.provider == "ctflow" and not args.allow_paid:
        print("ERROR: real provider runs require --allow-paid", file=sys.stderr)
        return 2
    if args.max_experiments < 1 or args.max_output_tokens < 1 or args.timeout_seconds <= 0 or args.provider_timeout_seconds <= 0:
        print("ERROR: positive execution limits are required", file=sys.stderr)
        return 2
    if args.max_cost_usd is None:
        configured = os.getenv("SCIENTIFIC_MAX_COST_USD")
        args.max_cost_usd = float(configured) if configured else 0.0
    try:
        run_matrix_arm(args)
        return 0 if json.loads((args.output.resolve() / "result.json").read_text(encoding="utf-8"))["status"] == "COMPLETED" else 3
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
