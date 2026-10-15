#!/usr/bin/env python3
"""Run only the missing real public checkpoints for G8 replicate 1/2."""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.scientific_discovery.models.provider import OpenAICompatibleProvider
from run_g7_failure_localization import Limits, case_prompt, public_tool_loop, system_prompt


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, value: dict[str, Any], lock: threading.Lock) -> None:
    line = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    with lock:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--base-checkpoints", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model-id", required=True)
    p.add_argument("--key-file", type=Path, required=True)
    p.add_argument("--base-url", required=True)
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--max-cost-usd", type=float, default=0.25)
    args = p.parse_args()
    if not 1 <= args.workers <= 16:
        raise SystemExit("workers must be in 1..16")
    public = {row["case_id"]: row for row in rows(args.public)}
    base = rows(args.base_checkpoints)
    base_by_pair = {(row["case_id"], row["group_id"]): row for row in base if row.get("status") == "completed"}
    if not base_by_pair:
        raise SystemExit("no completed base checkpoints")
    jobs = []
    for (case_id, group_id), row in sorted(base_by_pair.items()):
        for replicate in (1, 2):
            checkpoint_id = "g8cp_r%d_%s" % (replicate, hashlib.sha256(f"{case_id}|{group_id}|{replicate}".encode()).hexdigest()[:24])
            jobs.append({"checkpoint_id": checkpoint_id, "case_id": case_id, "group_id": group_id,
                         "replicate": replicate, "public_messages": row["public_messages"]})
    args.out.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.out / "g8_checkpoint_replicates.jsonl"
    done = {row["checkpoint_id"] for row in rows(checkpoint_path)} if checkpoint_path.exists() else set()
    jobs = [job for job in jobs if job["checkpoint_id"] not in done]
    lock = threading.Lock()

    def run(job: dict[str, Any]) -> str:
        trace_id = "checkpoint_" + job["checkpoint_id"]
        event_path = args.out / "checkpoint_traces" / trace_id / "events.jsonl"
        event_path.parent.mkdir(parents=True, exist_ok=True)
        # The imported G7 helper is used only for the public prompt/tool loop;
        # no labels, private oracle, or prior response is passed here.
        provider = OpenAICompatibleProvider(
            api_key=args.key_file.read_text(encoding="utf-8").strip(),
            base_url=args.base_url, model_name=args.model_id, timeout=args.timeout,
            max_retries=0, input_cost_per_1k=0.001, output_cost_per_1k=0.003,
            max_cost_usd=args.max_cost_usd, max_output_tokens=1024,
        )
        limits = Limits(16, 64, 32000, args.max_cost_usd)
        events: list[dict[str, Any]] = []
        # Reuse the exact public checkpoint messages, preserving the frozen
        # input.  The replicate is a bookkeeping field, not model-visible.
        messages = [dict(message) for message in job["public_messages"]]
        seq = 0
        def emit(event_type: str, status: str, payload: dict[str, Any]) -> None:
            nonlocal seq
            seq += 1
            events.append({"seq": seq, "ts_utc": time.time(), "run_id": trace_id,
                           "event_type": event_type, "status": status, "payload": payload})
        try:
            emit("RUN_START", "RUNNING", {"checkpoint_id": job["checkpoint_id"], "case_id": job["case_id"],
                                             "group_id": job["group_id"], "model_id": args.model_id,
                                             "public_only": True, "replicate": job["replicate"]})
            # Use the helper's durable event protocol in a temporary adapter
            # style by recording the output from its own trace events is not
            # possible; this runner emits a compact equivalent trace below.
            # The provider loop itself remains the project-tested loop.
            # We pass a real path and then merge helper events from that path.
            helper_trace = event_path.with_name("helper_events.jsonl")
            payload, _ = public_tool_loop(provider, messages, job["group_id"], limits,
                                          helper_trace, trace_id, 0, True)
            helper_events = rows(helper_trace) if helper_trace.exists() else []
            events.extend(helper_events)
            emit("RUN_END", "COMPLETED", {"status": "completed"})
            record = {"checkpoint_id": job["checkpoint_id"], "case_id": job["case_id"],
                      "group_id": job["group_id"], "replicate": job["replicate"],
                      "initial_decision": payload["decision"], "checkpoint_payload": payload,
                      "public_messages": job["public_messages"],
                      "trace_ref": str(event_path.relative_to(args.out)).replace("/", "\\"),
                      "trace_sha256": sha(helper_trace), "status": "completed", "public_only": True,
                      "source": "g8_real_checkpoint_replicate"}
            # Store the helper trace at the advertised path without changing
            # its append-only contents; the compact wrapper is not scored.
            event_path.write_text(helper_trace.read_text(encoding="utf-8"), encoding="utf-8")
            append_jsonl(checkpoint_path, record, lock)
            helper_trace.unlink()
            return "completed"
        except Exception as exc:
            try:
                emit("ERROR", "FAILED", {"error_type": type(exc).__name__, "error": str(exc)})
                emit("RUN_END", "FAILED", {"status": "provider_error"})
                event_path.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in events), encoding="utf-8")
            except Exception:
                pass
            append_jsonl(checkpoint_path, {"checkpoint_id": job["checkpoint_id"], "case_id": job["case_id"],
                                            "group_id": job["group_id"], "replicate": job["replicate"],
                                            "status": "provider_error", "trace_ref": str(event_path.relative_to(args.out)).replace("/", "\\")}, lock)
            return "provider_error"

    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="g8_checkpoint") as pool:
        futures = [pool.submit(run, job) for job in jobs]
        for future in as_completed(futures):
            result = future.result()
            counts[result] = counts.get(result, 0) + 1
            print(f"G8 checkpoint replicate progress: {sum(counts.values())}/{len(jobs)} {result}", flush=True)
    all_rows = rows(checkpoint_path) if checkpoint_path.exists() else []
    combined = [row for row in base if row.get("status") == "completed"] + [row for row in all_rows if row.get("status") == "completed"]
    combined.sort(key=lambda row: (row["case_id"], row["group_id"], int(row.get("replicate", 0))))
    combined_path = args.out / "g8_public_checkpoints_all.jsonl"
    combined_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in combined), encoding="utf-8")
    manifest = {"workers": args.workers, "requested_jobs": len(jobs), "counts": counts,
                "completed_checkpoint_rows": len(combined), "base_checkpoints_sha256": sha(args.base_checkpoints),
                "public_sha256": sha(args.public), "replicates": [0, 1, 2],
                "note": "Only missing G8 public checkpoints were run; provider failures remain explicit."}
    (args.out / "checkpoint_replicate_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if not counts.get("provider_error") else 2


if __name__ == "__main__":
    raise SystemExit(main())
