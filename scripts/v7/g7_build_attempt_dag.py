from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json


def _row(row: dict[str, Any], lineage: str, event_index: int) -> dict[str, Any]:
    attempt_id = str(row.get("attempt_id") or "")
    state_id = str(row.get("state_id") or attempt_id.split("::", 1)[0])
    trace_ref = row.get("trace_ref") or row.get("raw_path")
    return {
        "run_id": row.get("run_id") or state_id.split("_", 1)[0], "state_id": state_id,
        "parent_attempt_id": row.get("parent_attempt_id"), "attempt_id": attempt_id,
        "trace_id": str(trace_ref) if trace_ref else None, "checkpoint_id": row.get("checkpoint_id"),
        "arm": row.get("arm") or lineage, "request_id": row.get("request_id"),
        "timestamp": row.get("ended_at") or row.get("started_at"),
        "source_sha256": row.get("trace_sha256") or row.get("source_sha256"),
        "event_index": event_index, "failure_type": row.get("correction_reason") or row.get("historical_status"),
        "lineage_kind": row.get("lineage_kind") or lineage, "original_status": row.get("original_status") or row.get("state_status"),
        "original_defect_retained": bool(row.get("original_defect_retained", False)),
    }


def build(frozen: Path, recovery: Path, out: Path) -> dict[str, Any]:
    frozen_rows = read_jsonl(frozen); recovery_rows = read_jsonl(recovery)
    dag = [_row(row, "FROZEN_ORIGINAL", i) for i, row in enumerate(frozen_rows)]
    dag.extend(_row(row, "APPEND_ONLY_RECOVERY", len(dag) + i) for i, row in enumerate(recovery_rows))
    ids = [r["attempt_id"] for r in dag]
    failures = []
    if any(not x for x in ids): failures.append("missing_attempt_id")
    if len(ids) != len(set(ids)): failures.append("duplicate_attempt_id")
    for r in dag:
        if r["parent_attempt_id"] and r["parent_attempt_id"] not in set(ids): failures.append("parent_not_in_dag:" + r["attempt_id"])
        # A frozen row may carry an historical defect marker.  That marker is
        # evidence to retain, not evidence that the row was moved to recovery.
    write_jsonl(out, dag)
    result = {
        "frozen_count": len(frozen_rows), "recovery_count": len(recovery_rows), "dag_count": len(dag),
        "unique_attempts": len(set(ids)), "failures": failures,
        "frozen_source_sha256": sha256_file(frozen), "recovery_source_sha256": sha256_file(recovery),
        "append_only": True, "formal_frozen_denominator": 1288,
    }
    write_json(out.with_name("G7_DAG_BUILD_SUMMARY.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--frozen", type=Path, required=True); parser.add_argument("--recovery", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); result = build(args.frozen, args.recovery, args.out); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not result["failures"] else 2


if __name__ == "__main__": raise SystemExit(main())
