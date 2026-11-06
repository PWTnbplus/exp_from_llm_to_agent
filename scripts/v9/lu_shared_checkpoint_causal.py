from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import read_jsonl, write_json, write_jsonl


def review(base: Path, out: Path) -> dict:
    truth = {r["task_id"]: r for r in read_jsonl(base / "private_truth.jsonl")}; rows = read_jsonl(base / "records.jsonl"); scored = []
    for row in rows:
        if row.get("arm") == "INITIAL_CHECKPOINT": continue
        cand = row.get("candidate") or {}; text = json.dumps(cand, ensure_ascii=False).lower(); expected = truth[row["task_id"]]["real_status" if row["arm"] == "REAL" else "control_status"]
        relation = truth[row["task_id"]]["intervention_ir" if row["arm"] == "REAL" else "control_ir"]["relation"]
        nonfinal = any(token in text for token in ["non-final", "nonfinal", "intermediate", "u1"])
        relation_present = relation.lower() in text
        scored.append({**row, "independent_expected_status": expected, "independent_expected_relation": relation, "nonfinal_update_present": nonfinal, "relation_present": relation_present, "semantic_nonfinal_update_correct": bool(cand and nonfinal and relation_present), "truth_key_read_by_scorer": True})
    write_jsonl(out / "LU_U_V9_INDEPENDENT_SCORED.jsonl", scored)
    summary = {"protocol": "LU_V9_PROSPECTIVE_SHARED_CHECKPOINT_CONTROL_REAL_SHAM", "fork_rows": len(scored), "checkpoint_count": len({x.get("checkpoint_id") for x in scored}), "arm_counts": {a: sum(x.get("arm") == a for x in scored) for a in ["CONTROL", "REAL", "SHAM"]}, "semantic_correct": {a: sum(x.get("arm") == a and x["semantic_nonfinal_update_correct"] for x in scored) for a in ["CONTROL", "REAL", "SHAM"]}, "truth_key_sent_to_model": False, "shared_checkpoint_hashes_present": all(bool(x.get("shared_checkpoint_messages_sha256")) for x in scored)}
    write_json(out / "LU_U_V9_SUMMARY.json", summary); return summary


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--base", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True); print(json.dumps(review(args.base, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
