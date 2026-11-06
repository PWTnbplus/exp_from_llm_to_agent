"""Run an append-only thousand-unit G1--G5 Kimi cohort.

The existing v1/v2/v3 benchmark data remain immutable.  This runner uses
the public side of theory_benchmark_v2 and creates four predeclared technical
replicates (1,200 units per workflow).  Replicates are clustered by
``task_id`` in later analysis; they are not silently treated as 1,200
independent scientific laws.  Every workflow uses the same base model,
``kimi-k2.5``.  G4 and G5 are real Agent workflows through the normal
policy-enforced runner, not offline re-scoring.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_repair.cost_ledger import CostLedger
from scripts.run_single_kimi_g1_g3_canonical import LoggedProvider
from scripts.v9.provider import SingleKimiProvider
from src.scientific_discovery.theory_benchmark.runner import run_task
from src.scientific_discovery.theory_benchmark.schema import load_public_benchmark

MODEL = "kimi-k2.5"
GROUPS = ("G1", "G2", "G3", "G4", "G5")


def sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def select_tasks(public_tasks: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if limit is None or limit >= len(public_tasks):
        return public_tasks
    if limit < 1:
        raise ValueError("task-limit must be positive")
    # Preserve a fixed domain x difficulty balance for the compact thousand
    # unit expansion rather than taking a biased prefix of the source file.
    cells: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for task in public_tasks:
        cells.setdefault((str(task["domain"]), int(task["difficulty_level"])), []).append(task)
    ordered_cells = sorted(cells)
    base, remainder = divmod(limit, len(ordered_cells))
    selected: list[dict[str, Any]] = []
    for index, cell in enumerate(ordered_cells):
        selected.extend(cells[cell][: base + (1 if index < remainder else 0)])
    return sorted(selected, key=lambda task: str(task["task_id"]))


def run_one(item: tuple[str, int, dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    group, replicate, task = item
    task_id = str(task["task_id"])
    unit = f"{group}:replicate-{replicate:03d}:{task_id}"
    output_dir = args.run_root / "results" / group / f"replicate-{replicate:03d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(output_dir.glob(f"{group}__{task_id.replace(':', '__')}__*.json"))
    if args.resume:
        observed = []
        for path in existing:
            try:
                observed.append(json.loads(path.read_text(encoding="utf-8")).get("status"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
        if "COMPLETED" in observed:
            return {"group": group, "replicate": replicate, "task_id": task_id, "unit": unit, "status": "RESUMED_COMPLETED", "protocol_valid": True, "evaluator_valid": True, "answer_correct": False, "provider_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "elapsed_seconds": 0.0}
        if observed and not args.retry_failed:
            return {"group": group, "replicate": replicate, "task_id": task_id, "unit": unit, "status": "RESUMED_FAILED", "protocol_valid": False, "evaluator_valid": False, "answer_correct": False, "provider_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "elapsed_seconds": 0.0}
    trace_path = args.run_root / "logs" / "provider_traces" / group / f"replicate-{replicate:03d}" / f"{sha(task_id)[:20]}.jsonl"
    provider = SingleKimiProvider(
        args.run_root,
        args.key_file,
        args.base_url,
        MODEL,
        args.max_cost_usd,
        args.timeout,
        max_output_tokens=args.max_output_tokens,
        ledger_scope="g1-g5-thousand",
        ledger_worker=unit,
        ledger_ref_prefix=f"g1-g5-thousand:{unit}",
        protocol_label=f"{group}-INCREMENTAL-THOUSAND",
        ledger_path=args.run_root / "cost_ledger.sqlite",
        global_cap=200.0,
        worker_cap=args.max_cost_usd,
        raw_path=trace_path,
    )
    logged = LoggedProvider(provider, output_dir / f"provider_trace_{sha(task_id)[:20]}.jsonl")
    started = time.monotonic()
    try:
        result = run_task(task_id, logged, group, data_dir=args.data_dir, output_dir=output_dir)
        return {
            "group": group,
            "replicate": replicate,
            "task_id": task_id,
            "unit": unit,
            "status": result.get("status"),
            "protocol_valid": result.get("protocol_valid"),
            "evaluator_valid": result.get("evaluator_valid"),
            "answer_correct": bool((result.get("validation") or {}).get("answer_correct")),
            "provider_calls": int((result.get("metadata") or {}).get("provider_calls", 0) or 0),
            "input_tokens": int(((result.get("metadata") or {}).get("budget") or {}).get("used", {}).get("input_tokens", 0) or 0),
            "output_tokens": int(((result.get("metadata") or {}).get("budget") or {}).get("used", {}).get("output_tokens", 0) or 0),
            "cost_usd": float(((result.get("metadata") or {}).get("budget") or {}).get("used", {}).get("cost_usd", 0.0) or 0.0),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    except Exception as exc:
        # Preserve an explicit terminal runner failure as an observation.  The
        # predeclared denominator is never reduced because of an exception.
        return {
            "group": group,
            "replicate": replicate,
            "task_id": task_id,
            "unit": unit,
            "status": "RUNNER_EXCEPTION",
            "protocol_valid": False,
            "evaluator_valid": False,
            "answer_correct": False,
            "provider_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "theory_benchmark_v2")
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--replicates", type=int, default=4)
    parser.add_argument("--task-limit", type=int, default=None, help="fixed balanced public-task subset; use 200 for a 1,000-unit G1-G5 expansion")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--max-group-workers", type=int, default=4, help="per-group concurrency ceiling; explicit for unattended throughput tuning")
    parser.add_argument("--max-cost-usd", type=float, default=20.0)
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-failed", action="store_true", help="on resume, issue a fresh Kimi request for prior failed units")
    args = parser.parse_args()
    if args.replicates < 1 or args.workers < 1 or args.workers > 16 or args.max_group_workers < 1 or args.max_group_workers > 16:
        raise SystemExit("replicates must be positive, workers and max-group-workers must be in 1..16")
    if args.run_root.exists() and any(args.run_root.iterdir()) and not args.resume:
        raise SystemExit(f"refusing to reuse non-empty run root: {args.run_root}")
    args.run_root.mkdir(parents=True, exist_ok=True)
    public_tasks, public_manifest = load_public_benchmark(args.data_dir)
    source_task_count = len(public_tasks)
    public_tasks = select_tasks(public_tasks, args.task_limit)
    plan = [(group, replicate, task) for group in GROUPS for replicate in range(args.replicates) for task in public_tasks]
    manifest = {
        "protocol": "THEORY_BENCHMARK_V2_TECHNICAL_REPLICATION_V1",
        "model": MODEL,
        "only_model": True,
        "base_data_dir": str(args.data_dir.resolve()),
        "base_public_manifest": public_manifest,
        "base_public_sha256": sha(public_tasks),
        "groups": list(GROUPS),
        "base_tasks_per_group": len(public_tasks),
        "source_tasks_available": source_task_count,
        "task_selection": "balanced_domain_by_difficulty_prefix_within_each_cell" if args.task_limit is not None else "all_public_tasks",
        "replicates_per_group": args.replicates,
        "planned_units": len(plan),
        "replicate_semantics": "technical_replicates_clustered_by_task_id",
        "private_answer_key_copied": False,
        "private_answer_key_sent_to_model": False,
        "created_at_utc": utc_now(),
    }
    (args.run_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (args.run_root / "plans").mkdir(exist_ok=True)
    (args.run_root / "plans" / "public_plan.jsonl").write_text(
        "".join(json.dumps({"group": g, "replicate": r, "task_id": t["task_id"], "public_task_sha256": sha(t), "private_truth_sent": False}, ensure_ascii=False, sort_keys=True) + "\n" for g, r, t in plan),
        encoding="utf-8", newline="\n",
    )
    ledger = CostLedger(args.run_root / "cost_ledger.sqlite", global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd)
    del ledger
    ledger_path = args.run_root / "execution_ledger.jsonl"
    results: list[dict[str, Any]] = []
    # Tool-using and Agent arms can create several provider requests per
    # public task.  A single global pool therefore hides a much larger gateway
    # concurrency than ``--workers`` suggests.  Schedule groups sequentially
    # with explicit per-workflow ceilings and keep the public denominator fixed.
    group_workers = {group: min(args.workers, args.max_group_workers) for group in GROUPS}
    progress_index = 0
    for group in GROUPS:
        group_plan = [item for item in plan if item[0] == group]
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(group_workers[group], len(group_plan)), thread_name_prefix=f"{group.lower()}-kimi") as pool:
            futures = [pool.submit(run_one, item, args) for item in group_plan]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                results.append(row)
                progress_index += 1
                with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                if progress_index % 100 == 0 or row["status"] not in {"COMPLETED", "RESUMED_COMPLETED"}:
                    print(f"G1-G5 progress {progress_index}/{len(plan)} status={row['status']} group={row['group']} calls={row['provider_calls']}", flush=True)
    results.sort(key=lambda row: (row["group"], row["replicate"], row["task_id"]))
    summaries: dict[str, Any] = {}
    for group in GROUPS:
        subset = [row for row in results if row["group"] == group]
        summaries[group] = {
            "planned": len(subset),
            "terminal": sum(row["status"] in {"COMPLETED", "FAILED", "RESUMED_COMPLETED", "RESUMED_FAILED", "RUNNER_EXCEPTION"} for row in subset),
            "completed": sum(row["status"] in {"COMPLETED", "RESUMED_COMPLETED"} for row in subset),
            "correct": sum(row["answer_correct"] for row in subset),
            "partial_or_incorrect_or_failed": sum(not row["answer_correct"] for row in subset),
            "provider_calls": sum(row["provider_calls"] for row in subset),
            "input_tokens": sum(row["input_tokens"] for row in subset),
            "output_tokens": sum(row["output_tokens"] for row in subset),
            "total_tokens": sum(row["input_tokens"] + row["output_tokens"] for row in subset),
            "cost_usd": round(sum(row["cost_usd"] for row in subset), 9),
            "technical_failures": sum(row["status"] not in {"COMPLETED", "RESUMED_COMPLETED"} for row in subset),
            "accuracy_all_planned": sum(row["answer_correct"] for row in subset) / max(1, len(subset)),
            "accuracy_completed_only": sum(row["answer_correct"] for row in subset if row["status"] in {"COMPLETED", "RESUMED_COMPLETED"}) / max(1, sum(row["status"] in {"COMPLETED", "RESUMED_COMPLETED"} for row in subset)),
        }
        (args.run_root / f"summary_{group}.json").write_text(json.dumps(summaries[group], ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    summary = {"manifest": manifest, "totals": summaries, "completed_at_utc": utc_now(), "cost_ledger": CostLedger(args.run_root / "cost_ledger.sqlite", global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd).snapshot()}
    (args.run_root / "execution_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
