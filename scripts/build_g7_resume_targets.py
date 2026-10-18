#!/usr/bin/env python3
"""Freeze an append-only recovery target list from audited G7 state views.

The output is a small routing artifact, not a replacement denominator.  It
contains every non-completed state plus the 13 independently identified
historical final-attempt trace defects.  Raw state files and trace history are
never changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--trace-incidents", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    plan = read_jsonl(args.plan)
    states = {row["run_id"]: row for row in read_jsonl(args.states)}
    incidents = read_jsonl(args.trace_incidents)
    trace_retry_ids = {
        row["run_id"] for row in incidents
        if row.get("classification") == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY"
    }
    plan_ids = {row["run_id"] for row in plan}
    unknown_incidents = sorted(trace_retry_ids - plan_ids)
    if unknown_incidents:
        raise SystemExit(f"trace incident IDs are not in frozen plan: {unknown_incidents[:5]}")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in plan:
        run_id = row["run_id"]
        state = states.get(run_id, {})
        status = state.get("status", "missing_state")
        if status != "completed" or run_id in trace_retry_ids:
            is_terminal = status != "completed"
            is_trace_retry = run_id in trace_retry_ids
            category = (
                "TERMINAL_STATE_AND_TRACE_RETRY" if is_terminal and is_trace_retry
                else "TERMINAL_STATE" if is_terminal
                else "TRACE_RETRY"
            )
            rows.append({
                "run_id": run_id,
                "category": category,
                "prior_status": status,
                "prior_trace_ref": state.get("trace_ref"),
                "historical_attempt_preserved": True,
            })
            seen.add(run_id)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "kind": "g7_append_only_resume_targets",
        "plan_sha256": sha256(args.plan),
        "states_sha256": sha256(args.states),
        "trace_incidents_sha256": sha256(args.trace_incidents),
        "plan_rows": len(plan),
        "target_rows": len(rows),
        "terminal_state_targets": sum(states.get(row["run_id"], {}).get("status") != "completed" for row in rows),
        "trace_retry_targets": len(trace_retry_ids),
        "overlap_targets": sum(row["category"] == "TERMINAL_STATE_AND_TRACE_RETRY" for row in rows),
        "unique_target_ids": len(seen),
        "pooling_prohibited": True,
        "historical_failures_retained": True,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
