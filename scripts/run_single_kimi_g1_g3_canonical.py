"""Run immutable, single-model G1--G3 theory-benchmark cohorts.

The runner uses the existing answer-separated ``run_task`` implementation and
the repository's append-only Kimi provider/ledger adapter.  It creates a new
run root, freezes a public-only plan before the first request, and never copies
or sends the private answer key to the model.  Existing result directories are
never used as an output target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow the runner to be launched from the shared workspace as well as from
# the repository root.  This does not alter the protocol or data paths.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.v9.common import append_jsonl
from scripts.audit_repair.cost_ledger import CostLedger
from scripts.v9.provider import SingleKimiProvider
from src.scientific_discovery.theory_benchmark.runner import run_task
from src.scientific_discovery.theory_benchmark.schema import load_public_benchmark
from src.scientific_discovery.experiment.policy import get_group_policy


MODEL = "kimi-k2.5"
GROUPS = ("G1", "G2", "G3")


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class LoggedProvider:
    """Expose the normal provider protocol while retaining raw trace rows."""

    def __init__(self, kimi: SingleKimiProvider, log_path: Path) -> None:
        self.inner = kimi.provider
        self.kimi = kimi
        self.log_path = log_path
        self.model_name = self.inner.model_name
        self.max_cost_usd = self.inner.max_cost_usd
        self.max_retries = self.inner.max_retries
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> Any:
        before = len(self.inner.audit_trace())
        try:
            response = self.inner.complete(messages, tools=tools)
        except Exception as exc:
            append_jsonl(self.log_path, {
                "record_type": "provider_error",
                "model_id": MODEL,
                "error_type": type(exc).__name__,
                "request_sha256": canonical_hash({"messages": messages, "tools": tools}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            raise
        traces = self.inner.audit_trace()[before:]
        for trace in traces:
            append_jsonl(self.log_path, {
                "record_type": "provider_trace",
                "model_id": MODEL,
                "trace": trace,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return response

    def audit_trace(self) -> list[dict[str, Any]]:
        return self.inner.audit_trace()


def freeze_plan(run_root: Path, public_tasks: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    plans = run_root / "plans"
    plans.mkdir(parents=True, exist_ok=False)
    public_hash = canonical_hash(public_tasks)
    (plans / "public_plan_manifest.json").write_text(json.dumps({
        "protocol": "theory-benchmark-v1-public-only",
        "model": MODEL,
        "public_task_count": len(public_tasks),
        "public_tasks_sha256": public_hash,
        "private_answer_key_sent_to_model": False,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "run_manifest_sha256": canonical_hash(manifest),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    with (plans / "public_plan.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for group in GROUPS:
            for task in public_tasks:
                handle.write(json.dumps({
                    "group": group,
                    "task_id": task["task_id"],
                    "public_task_sha256": canonical_hash(task),
                    "protocol": get_group_policy(group).as_dict(),
                }, ensure_ascii=False, sort_keys=True) + "\n")


def is_valid_result(path: Path, task_id: str, group: str) -> bool:
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    # A terminal model/protocol failure is still a real observation and must
    # not be silently retried on resume.  Resuming only completed rows would
    # turn a fixed plan into an opportunistic denominator and would erase the
    # distinction between model errors and transport errors.  The audit layer
    # reports these statuses separately.
    return (
        row.get("task_id") == task_id
        and row.get("group") == group
        and row.get("model_id") == MODEL
        and row.get("status") in {"COMPLETED", "FAILED"}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--max-cost-usd", type=float, default=20.0)
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if args.run_root.exists():
        if not args.resume:
            raise SystemExit(f"refusing to reuse existing run root without --resume: {args.run_root}")
    else:
        args.run_root.mkdir(parents=True)

    public_tasks, public_manifest = load_public_benchmark(args.data_dir)
    if args.limit is not None:
        public_tasks = public_tasks[:args.limit]
    if not public_tasks:
        raise SystemExit("no public tasks selected")

    manifest = {
        "experiment": "single-kimi-g1-g3-canonical",
        "protocol": "theory-benchmark-v1",
        "model": MODEL,
        "only_model": True,
        "groups": list(GROUPS),
        "public_task_count_per_group": len(public_tasks),
        "planned_units": len(public_tasks) * len(GROUPS),
        "public_manifest": public_manifest,
        "public_tasks_sha256": canonical_hash(public_tasks),
        "answer_key_copied": False,
        "private_answer_key_sent_to_model": False,
        "provider": "openai-compatible-kimi",
        "base_url": args.base_url,
        "model_id": MODEL,
        "max_transport_retries": 0,
        "max_output_tokens": args.max_output_tokens,
        "max_cost_usd": args.max_cost_usd,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "scripts/run_single_kimi_g1_g3_canonical.py",
    }
    manifest_path = args.run_root / "manifest.json"
    if not manifest_path.exists():
        freeze_plan(args.run_root, public_tasks, manifest)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    execution_log = args.run_root / "execution_ledger.jsonl"
    totals: dict[str, dict[str, int | float]] = {}
    for group in GROUPS:
        output_dir = args.run_root / "results" / group
        output_dir.mkdir(parents=True, exist_ok=True)
        completed = 0
        correct = 0
        attempted = 0
        for task in public_tasks:
            task_id = task["task_id"]
            prefix = f"{group}__{task_id.replace(':', '__')}__"
            candidates = sorted(output_dir.glob(f"{prefix}*.json"))
            if args.resume and any(is_valid_result(path, task_id, group) for path in candidates):
                append_jsonl(execution_log, {"group": group, "task_id": task_id, "status": "RESUMED_VALID"})
                completed += 1
                continue
            attempted += 1
            started = time.monotonic()
            try:
                # The runner records the provider trace returned by the
                # provider object.  A fresh view per task prevents previous
                # tasks' traces from being re-accounted into the current
                # task's local BudgetLedger.  The SQLite ledger remains
                # shared, so the cumulative spending ceiling is atomic.
                kimi = SingleKimiProvider(
                    run=args.run_root,
                    key_file=args.key_file,
                    base_url=args.base_url,
                    model_id=MODEL,
                    max_cost=args.max_cost_usd,
                    timeout=args.timeout,
                    max_output_tokens=args.max_output_tokens,
                    ledger_scope="g0-g3-canonical",
                    ledger_worker="single-kimi-g0-g3",
                    ledger_ref_prefix=f"g0-g3-canonical:{group}:{task_id}",
                    protocol_label="G0-G3-CANONICAL",
                    ledger_path=args.run_root / "cost_ledger.sqlite",
                    global_cap=200.0,
                    worker_cap=args.max_cost_usd,
                )
                provider = LoggedProvider(kimi, args.run_root / "logs" / "provider_traces.jsonl")
                result = run_task(task_id, provider, group, data_dir=args.data_dir, output_dir=output_dir)
                completed += result.get("status") == "COMPLETED"
                correct += result.get("validation", {}).get("answer_correct", False)
                append_jsonl(execution_log, {
                    "group": group,
                    "task_id": task_id,
                    "status": result.get("status"),
                    "protocol_valid": result.get("protocol_valid"),
                    "evaluator_valid": result.get("evaluator_valid"),
                    "answer_correct": result.get("validation", {}).get("answer_correct", False),
                    "provider_calls": (result.get("metadata") or {}).get("provider_calls", 0),
                    "cost_usd": ((result.get("metadata") or {}).get("budget") or {}).get("used", {}).get("cost_usd", 0.0),
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                })
            except Exception as exc:
                append_jsonl(execution_log, {
                    "group": group,
                    "task_id": task_id,
                    "status": "RUNNER_EXCEPTION",
                    "error_type": type(exc).__name__,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                })
        totals[group] = {"planned": len(public_tasks), "attempted": attempted, "completed": int(completed), "correct": int(correct)}
        (args.run_root / f"summary_{group}.json").write_text(json.dumps(totals[group], indent=2) + "\n", encoding="utf-8", newline="\n")

    trace_path = args.run_root / "logs" / "provider_traces.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()] if trace_path.exists() else []
    observed_cost = sum(float((((row.get("trace") or {}).get("response") or {}).get("usage") or {}).get("cost_usd", 0.0) or 0.0) for row in trace_rows if row.get("record_type") == "provider_trace")
    ledger_snapshot = CostLedger(args.run_root / "cost_ledger.sqlite", global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd).snapshot()
    summary = {
        "run_root": str(args.run_root),
        "model": MODEL,
        "only_model": True,
        "totals": totals,
        "provider_reserved_cost_usd": round(float(ledger_snapshot["settled_new_usd"] + ledger_snapshot["inflight_reserved_usd"]), 9),
        "provider_observed_cost_usd": round(observed_cost, 9),
        "provider_trace_count": sum(row.get("record_type") == "provider_trace" for row in trace_rows),
        "provider_error_record_count": sum(row.get("record_type") == "provider_error" for row in trace_rows),
        "cost_ledger": ledger_snapshot,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    (args.run_root / "execution_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
