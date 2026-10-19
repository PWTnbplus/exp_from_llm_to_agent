from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .claim_ir import ClaimIR
from .common import read_jsonl, write_json, write_jsonl
from .math_verifier import verify_claim


def review(base: Path, out: Path) -> dict[str, Any]:
    public = {r["task_id"]: r for r in read_jsonl(base / "public_cases.jsonl")}; truth = {r["task_id"]: r for r in read_jsonl(base / "private_truth.jsonl")}; records = read_jsonl(base / "records.jsonl")
    scored = []
    for row in records:
        task = public[row["task_id"]]; expected = truth[row["task_id"]]; candidate = row.get("candidate") or {}; dsl = candidate.get("proposition_DSL") or {}; expected_dsl = task["proposition_dsl"]
        dsl_match = all(dsl.get(k) == v for k, v in expected_dsl.items()); action = str(candidate.get("proposed_final_action", "")).upper(); proof = verify_claim(ClaimIR(**expected["claim_ir"]))
        scored.append({**row, "independent_sympy_status": proof["status"], "independent_certificate_sha256": proof["certificate_sha256"], "dsl_matches_public": dsl_match, "action_schema_valid": action in {"PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN"}, "state_correct": dsl_match and action == expected["expected_status"], "truth_key_read_by_scorer": True})
    write_jsonl(out / "Q_V9_INDEPENDENT_REVIEW.jsonl", scored)
    summary = {"protocol": "Q_KIMI_V9_TRUTH_FIRST_INDEPENDENT_REVIEW", "rows": len(scored), "schema_valid": sum(x["action_schema_valid"] for x in scored), "state_correct": sum(x["state_correct"] for x in scored), "sympy_status_counts": {s: sum(x["independent_sympy_status"] == s for x in scored) for s in ["PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN"]}, "private_truth_read_after_model_calls": True, "truth_key_sent_to_model": False}
    write_json(out / "Q_V9_REVIEW_SUMMARY.json", summary); return summary


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--base", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True); print(json.dumps(review(args.base, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
