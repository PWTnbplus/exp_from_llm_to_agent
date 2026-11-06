#!/usr/bin/env python3
"""Low-concurrency, resumable real-Kimi runner for the G8.5 cohort."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.g85_prospective_history_pairs import BASE_URL, MODEL_ID, PROTOCOL
from scripts.v9.common import append_jsonl, extract_json, read_jsonl, sha_obj, write_json
from scripts.v9.provider import SingleKimiProvider


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_one(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    key = (row["pair_id"], row["history_kind"])
    stem = sha_obj({"pair_id": key[0], "history_kind": key[1]})[:24]
    record_path = args.run_root / "records" / f"{stem}.json"
    if record_path.exists():
        return json.loads(record_path.read_text(encoding="utf-8"))
    provider = SingleKimiProvider(
        args.run_root,
        args.key_file,
        args.base_url,
        MODEL_ID,
        args.max_cost,
        args.timeout,
        max_output_tokens=args.max_output_tokens,
        ledger_scope="g85",
        ledger_worker=f"g85:{row['pair_id']}:{row['history_kind']}",
        ledger_ref_prefix=f"g85:{row['pair_id']}:{row['history_kind']}",
        protocol_label=PROTOCOL,
        ledger_path=args.run_root / "cost_ledger.sqlite",
        global_cap=200.0,
        worker_cap=args.max_cost,
        raw_path=args.run_root / "logs" / "provider_traces" / f"{stem}.jsonl",
    )
    system = "You are a public scientific-history recorder using only the supplied problem and evidence. Never access private truth, files, network, hidden answers, or prior hidden tasks. Return JSON only with history_events, state_after, evidence_used, and recovery_status."
    user = {
        "pair_id": row["pair_id"],
        "canonical_state_id": row["canonical_state_id"],
        "evidence_id": row["evidence_id"],
        "problem": row["problem"],
        "public_evidence": row["evidence"],
        "history_kind": row["history_kind"],
        "instruction": row["public_history_instruction"],
    }
    result = provider.call(PROTOCOL, f"{row['pair_id']}:{row['history_kind']}", row["history_kind"], [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False, sort_keys=True)}])
    candidate = None
    status = "SUCCESS"
    if result.get("content"):
        try:
            candidate = extract_json(result["content"])
        except Exception:
            status = "INVALID_OR_TRUNCATED_RESPONSE"
    else:
        status = "PROVIDER_ERROR"
    record = {
        "protocol": PROTOCOL,
        "pair_id": row["pair_id"],
        "canonical_state_id": row["canonical_state_id"],
        "evidence_id": row["evidence_id"],
        "history_kind": row["history_kind"],
        "history_provenance": "prospective_controlled",
        "candidate": candidate,
        "raw_content_present": bool(result.get("content")),
        "provider_error": result.get("error"),
        "call_number": result["call_number"],
        "usage": result.get("usage") or {},
        "private_truth_injected": False,
        "input_sha256": sha_obj(user),
        "terminal_status": status,
        "created_at_utc": utc_now(),
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(record_path, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-cost", type=float, default=20.0)
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()
    if not 1 <= args.workers <= 2:
        raise SystemExit("G8.5 workers must be 1 or 2 to keep gateway concurrency bounded")
    plan = read_jsonl(args.plan)
    args.run_root.mkdir(parents=True, exist_ok=True)
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    history_path = args.run_root / "history_records.jsonl"
    for record in read_jsonl(history_path):
        existing[(record.get("pair_id"), record.get("history_kind"))] = record
    for path in (args.run_root / "records").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        existing.setdefault((record.get("pair_id"), record.get("history_kind")), record)
    jobs = [row for row in plan if (row["pair_id"], row["history_kind"]) not in existing]
    statuses: dict[str, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="g85-kimi") as pool:
        futures = [pool.submit(run_one, row, args) for row in jobs]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            record = future.result()
            existing[(record["pair_id"], record["history_kind"])] = record
            statuses[record["terminal_status"]] = statuses.get(record["terminal_status"], 0) + 1
            if index % 25 == 0 or record["terminal_status"] != "SUCCESS":
                print(f"G8.5 progress {index}/{len(jobs)} status={record['terminal_status']} pair={record['pair_id']}", flush=True)
    # Append only missing records; never rewrite a prior history record.
    written = {(record.get("pair_id"), record.get("history_kind")) for record in read_jsonl(history_path)}
    for row in plan:
        key = (row["pair_id"], row["history_kind"])
        record = existing.get(key)
        if record and key not in written:
            append_jsonl(history_path, record)
            written.add(key)
    # Provider traces are append-only one-file-per-unit records.  The previous
    # summary reader looked for a non-existent aggregate file and reported
    # zero calls even when the raw traces and record usage were present.
    trace_paths = sorted((args.run_root / "logs" / "provider_traces").glob("*.jsonl"))
    traces = [trace for path in trace_paths for trace in read_jsonl(path)]
    usages = [((trace.get("trace") or {}).get("response") or {}).get("usage", {}) for trace in traces]
    input_tokens = sum(int(usage.get("input_tokens", 0) or 0) for usage in usages)
    output_tokens = sum(int(usage.get("output_tokens", 0) or 0) for usage in usages)
    total_tokens = sum(int(usage.get("total_tokens") or (int(usage.get("input_tokens", 0) or 0) + int(usage.get("output_tokens", 0) or 0))) for usage in usages)
    total_cost = sum(float(usage.get("cost_usd", 0.0) or 0.0) for usage in usages)
    summary = {"protocol": PROTOCOL, "model_id": MODEL_ID, "only_model": True, "planned": len(plan), "recorded": len(written), "new_jobs": len(jobs), "new_status_counts": statuses, "real_provider_calls": len(traces), "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens, "total_cost_usd": round(total_cost, 9), "private_truth_injected": False, "history_provenance": "prospective_controlled"}
    write_json(args.summary_out or (args.run_root / "execution_summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if len(written) == len(plan) else 2


if __name__ == "__main__":
    raise SystemExit(main())
