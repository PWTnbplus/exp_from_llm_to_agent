from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from .common import read_jsonl, write_json


def ci(rows: list[dict[str, Any]], cluster_key: str, score_key: str, reps: int = 4000) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for row in rows: groups.setdefault(str(row.get(cluster_key)), []).append(float(bool(row.get(score_key))))
    if not groups: return {"n": 0, "clusters": 0, "estimate": None, "ci95": None}
    names = list(groups); values = [v for g in groups.values() for v in g]; estimate = sum(values) / len(values); rng = random.Random(20261019); boot = []
    for _ in range(reps):
        sampled = [rng.choice(names) for _ in names]; flattened = [v for name in sampled for v in groups[name]]; boot.append(sum(flattened) / len(flattened))
    boot.sort(); return {"n": len(values), "clusters": len(groups), "estimate": estimate, "ci95": [boot[int(reps * .025)], boot[int(reps * .975) - 1]], "cluster_key": cluster_key, "score_key": score_key, "bootstrap": reps}


def run(run: Path, audit: Path) -> dict[str, Any]:
    g6 = read_jsonl(run / "g6/records_scored.jsonl"); q = read_jsonl(audit / "Q_V9_INDEPENDENT_REVIEW.jsonl"); lu = read_jsonl(audit / "LU_U_V9_INDEPENDENT_SCORED.jsonl"); g7 = read_jsonl(run / "g7/G7_V9_INDEPENDENT_SCORED.jsonl"); g7_repair = read_jsonl(run / "g7_repair/G7_REPAIR_INDEPENDENT_SCORED.jsonl"); ac = read_jsonl(run / "agent_comparison/records_scored.jsonl")
    stats = {
        "G6_V9": {"strict_action": ci(g6, "family_id", "action_correct"), "by_arm": {a: ci([r for r in g6 if r.get("arm_id") == a], "family_id", "action_correct") for a in ["G6_A_G3_GIVEN", "G6_B_G4_GIVEN"]}, "by_cf": {c: ci([r for r in g6 if r.get("cf_type") == c], "family_id", "action_correct") for c in ["CF1", "CF2", "CF3", "CF4"]}},
        "Q_V9": {"action_schema": ci(q, "task_id", "action_schema_valid"), "mathematical_state": ci(q, "task_id", "state_correct")},
        "LU_U_V9": {"semantic_update": ci(lu, "task_id", "semantic_nonfinal_update_correct"), "by_arm": {a: ci([r for r in lu if r.get("arm") == a], "task_id", "semantic_nonfinal_update_correct") for a in ["CONTROL", "REAL", "SHAM"]}},
        "G7_V9": {"stage_adherence": ci(g7, "task_id", "stage_adherent"), "final_accuracy_all_planned_strict": ci([r for r in g7 if r.get("stage") == "D3_VLU"], "task_id", "final_correct"), "final_accuracy_all_planned_semantic": ci([r for r in g7 if r.get("stage") == "D3_VLU"], "task_id", "final_semantic_correct"), "by_stage": {s: ci([r for r in g7 if r.get("stage") == s], "task_id", "stage_adherent") for s in ["D0", "D1_V", "D2_VL", "D3_VLU"]}},
        "G7_V9_REPAIR_PUBLIC_EQUATION": {"stage_adherence": ci(g7_repair, "task_id", "stage_adherent"), "final_accuracy_all_planned_strict": ci([r for r in g7_repair if r.get("stage") == "D3_VLU"], "task_id", "final_correct"), "final_accuracy_all_planned_semantic": ci([r for r in g7_repair if r.get("stage") == "D3_VLU"], "task_id", "final_semantic_correct"), "by_stage": {s: ci([r for r in g7_repair if r.get("stage") == s], "task_id", "stage_adherent") for s in ["D0", "D1_V", "D2_VL", "D3_VLU"]}},
        "AGENT_COMPARISON_V9": {"action_valid": ci(ac, "task_id", "action_valid"), "by_workflow": {w: ci([r for r in ac if r.get("workflow") == w], "task_id", "action_valid") for w in ["LLM_ONLY", "AGENT"]}, "adaptive_feedback_records": sum(bool(r.get("observation_feedback_received")) for r in ac)},
    }
    write_json(audit / "V9_PAIRED_CLUSTERED_STATISTICS.json", stats); return stats


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--run", type=Path, required=True); parser.add_argument("--audit", type=Path, required=True); args = parser.parse_args(); print(json.dumps(run(args.run, args.audit), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
