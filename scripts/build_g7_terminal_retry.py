#!/usr/bin/env python3
"""Build an immutable, separately identified retry plan for G7 terminal rows.

The historical G7 plan/states are read-only inputs. This script selects only
rows whose canonical state is terminal, creates deterministic retry IDs, and
records source IDs and hashes in every retry row. It never merges retry results
into the historical run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def readl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, source_id: str) -> str:
    return f"{prefix}_{hashlib.sha256(source_id.encode('utf-8')).hexdigest()[:20]}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--states", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()

    plan = readl(args.plan)
    states = readl(args.states)
    if not plan or not states:
        raise SystemExit("plan and states are required")
    state_by_run = {row["run_id"]: row for row in states}
    terminal = [row for row in plan if state_by_run.get(row["run_id"], {}).get("status") != "completed"]
    if not terminal:
        raise SystemExit("no terminal rows found")

    out_rows: list[dict[str, Any]] = []
    for row in terminal:
        source_run = row["run_id"]
        source_cp = row["checkpoint_id"]
        retry = dict(row)
        retry["run_id"] = stable_id("g7r", source_run)
        retry["checkpoint_id"] = stable_id("g7rcp", source_cp)
        retry["source_run_id"] = source_run
        retry["source_checkpoint_id"] = source_cp
        retry["retry_scope"] = "terminal_rows_only"
        retry["retry_protocol"] = "separate_frozen_retry_not_pooled"
        out_rows.append(retry)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in out_rows),
        encoding="utf-8",
    )
    manifest = {
        "kind": "g7_terminal_retry_plan",
        "status": "FROZEN_SEPARATE_RETRY",
        "source_plan": str(args.plan),
        "source_states": str(args.states),
        "source_plan_sha256": sha256(args.plan),
        "source_states_sha256": sha256(args.states),
        "retry_plan_sha256": sha256(args.out),
        "source_plan_rows": len(plan),
        "retry_rows": len(out_rows),
        "retry_unique_source_runs": len({row["source_run_id"] for row in out_rows}),
        "retry_unique_source_checkpoints": len({row["source_checkpoint_id"] for row in out_rows}),
        "source_terminal_status_counts": {},
        "pooling_prohibited": True,
    }
    counts: dict[str, int] = {}
    for row in terminal:
        state = state_by_run.get(row["run_id"])
        status = str(state.get("status")) if state is not None else "missing_state"
        counts[status] = counts.get(status, 0) + 1
    manifest["source_terminal_status_counts"] = counts
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
