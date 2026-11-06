from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .common import read_jsonl, write_jsonl, write_json


def score_g6(base: Path) -> dict:
    truth = {r["case_id"]: r for r in read_jsonl(base / "private_truth.jsonl")}; out = []
    for row in read_jsonl(base / "records.jsonl"):
        cand = row.get("candidate") or {}; observed = str(cand.get("decision", "")).upper(); t = truth[row["case_id"]]
        out.append({**row, "expected_action": t["expected_action"], "action_correct": observed == t["expected_action"], "structure_valid": observed in {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"} and isinstance(cand.get("affected_claim_ids", []), list), "truth_key_read_by_scorer": True})
    write_jsonl(base / "records_scored.jsonl", out); return {"rows": len(out), "action_correct": sum(x["action_correct"] for x in out), "structure_valid": sum(x["structure_valid"] for x in out)}


def score_g7(base: Path, output_name: str = "G7_V9_INDEPENDENT_SCORED.jsonl") -> dict:
    truth = {r["task_id"]: r for r in read_jsonl(base / "private_truth.jsonl")}; out = []
    for row in read_jsonl(base / "records.jsonl"):
        cand = row.get("candidate") or {}; text = json.dumps(cand, ensure_ascii=False).lower(); stage = row["stage"]
        if stage == "D0": adherent = bool(cand) and any(x in text for x in ["audit", "complete", "inspect"])
        elif stage == "D1_V": adherent = bool(cand) and any(x in text for x in ["next", "d2", "lemma", "proceed"])
        elif stage == "D2_VL": adherent = bool(cand) and any(x in text for x in ["d3", "advance", "lemma", "complete"])
        else: adherent = bool(cand) and all(token.lower() in text for token in ["v", "l", "u"])
        final_correct = False
        final_semantic_correct = False
        if stage == "D3_VLU":
            expected = truth[row["task_id"]]["expected_relation"].lower()
            final_correct = expected in text and any(token in text for token in ["true", "accepted", "approved", "proven"])
            # The strict metric above requires an explicit truth-status token.
            # This separate preregistered semantic metric asks whether the
            # public equation/relation is actually carried into the VLU->Y
            # inference, without treating a generic graph acknowledgement as
            # a correct mathematical answer.
            final_semantic_correct = expected in text and any(token in text for token in ["infer", "audit", "accept", "complete"])
        out.append({**row, "stage_adherent": adherent, "final_correct": final_correct, "final_semantic_correct": final_semantic_correct, "private_Y_injected_verified_false": row.get("private_Y_injected") is False, "truth_key_read_by_scorer": True})
    write_jsonl(base / output_name, out); return {"rows": len(out), "stage_adherent": sum(x["stage_adherent"] for x in out), "final_planned": sum(x["stage"] == "D3_VLU" for x in out), "final_correct": sum(x["final_correct"] for x in out if x["stage"] == "D3_VLU"), "private_Y_injected": any(x["private_Y_injected"] for x in out)}


def score_agent(base: Path) -> dict:
    out = []
    for row in read_jsonl(base / "records.jsonl"):
        cand = row.get("candidate") or {}
        actions = []
        for key in ["action", "next_action", "action_1", "action_2"]:
            if key in cand: actions.append(cand[key])
        conclusion = cand.get("conclusion") or {}
        for key in ["chosen_action", "best_action"]:
            if key in conclusion: actions.append(conclusion[key])
        valid = bool(actions) and all(isinstance(action, dict) and set(action) == {"x"} and isinstance(action.get("x"), (int, float)) and action["x"] in {0, 1, 2} for action in actions)
        out.append({**row, "action_valid": valid, "adaptive_feedback_recorded": row.get("workflow") == "AGENT" and bool(row.get("observation_feedback_received"))})
    write_jsonl(base / "records_scored.jsonl", out); return {"rows": len(out), "action_valid": sum(x["action_valid"] for x in out), "agent_feedback_records": sum(x["adaptive_feedback_recorded"] for x in out)}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--run", type=Path, required=True); args = parser.parse_args(); result = {"g6": score_g6(args.run / "g6"), "g7": score_g7(args.run / "g7"), "agent_comparison": score_agent(args.run / "agent_comparison")}; write_json(args.run / "SCORING_RESULT.json", result); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
