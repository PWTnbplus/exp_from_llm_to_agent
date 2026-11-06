from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json


def build(tasks: Path, records: Path, traces: Path, out: Path) -> dict:
    task_rows, record_rows, trace_rows = read_jsonl(tasks), read_jsonl(records), read_jsonl(traces)
    by_task = {}
    for row in record_rows: by_task.setdefault(row.get("task_id"), []).append(row)
    paired = []
    for task in task_rows:
        arms = {row.get("arm"): row for row in by_task.get(task.get("task_id"), [])}
        paired.append({
            "pair_id": "v7-pair:" + str(task.get("task_id")), "task_id": task.get("task_id"), "workflow": "single_kimi_public_calibration",
            "model_id": sorted({x.get("model_id") for x in arms.values() if x.get("model_id")}), "arms_present": sorted(arms),
            "control_record": arms.get("control"), "real_intervention_record": arms.get("intervention"), "sham_record": None,
            "trace_count": sum(1 for t in trace_rows if t.get("task_id") == task.get("task_id")),
            "checkpoint_id": None, "before_observed_from_checkpoint": False,
            "u_eligibility": "INELIGIBLE_U", "reason": "reused calls lack immutable shared checkpoint and sham arm",
        })
    write_jsonl(out, paired)
    result = {"pair_count": len(paired), "complete_control_intervention": sum(bool(x["control_record"] and x["real_intervention_record"]) for x in paired), "valid_u_pairs": 0, "trace_source_sha256": sha256_file(traces), "private_truth_read": False}
    write_json(out.with_name("LU_PAIRED_COHORT_MANIFEST.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--tasks", type=Path, required=True); parser.add_argument("--records", type=Path, required=True); parser.add_argument("--traces", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(build(args.tasks, args.records, args.traces, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
