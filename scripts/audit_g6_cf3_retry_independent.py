"""Run the independent public-only mathematical audit for a G6 CF3 retry.

This audit deliberately does not load the private oracle.  It scores only the
candidate claim against the narrow, fail-closed public verifier and stores a
claim hash rather than model prose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.audit_repair.math_verifier import verify_candidate_claim, verifier_sha256


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--out-audit", type=Path, required=True)
    parser.add_argument("--out-summary", type=Path, required=True)
    args = parser.parse_args()

    plan = read_jsonl(args.plan)
    public = {row["case_id"]: row for row in read_jsonl(args.public)}
    responses = {row["run_id"]: row for row in read_jsonl(args.responses)}
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for plan_row in plan:
        run_id = plan_row["run_id"]
        response = responses.get(run_id)
        case = public.get(plan_row["case_id"], {})
        visible = case.get("model_visible", {})
        claim = response.get("revised_claim") if response else None
        if response is None:
            failures.append(f"missing_response:{run_id}")
            verdict = verify_candidate_claim(
                cf_type=str(plan_row.get("cf_type")),
                claim=None,
                quantifier=str(case.get("quantifier", "")),
                public_problem=str(visible.get("original_problem", "")),
            )
        else:
            verdict = verify_candidate_claim(
                cf_type=str(plan_row.get("cf_type")),
                claim=claim,
                quantifier=str(case.get("quantifier", "")),
                public_problem=str(visible.get("original_problem", "")),
            )
        rows.append(
            {
                "run_id": run_id,
                "case_id": plan_row["case_id"],
                "cf_type": plan_row.get("cf_type"),
                "decision": response.get("decision") if response else None,
                "response_status": response.get("status") if response else None,
                "candidate_claim_sha256": hashlib.sha256(claim.encode("utf-8")).hexdigest() if isinstance(claim, str) else None,
                "status": verdict.status,
                "grade": verdict.grade,
                "proof_kind": verdict.proof_kind,
                "reason_code": verdict.reason_code,
                "evidence": verdict.evidence,
                "verifier_version": "audit_repair.math_verifier.v1",
                "verifier_source_sha256": verifier_sha256(),
                "independent_of_private_oracle": True,
            }
        )
    if len(rows) != len(plan) or len({row["run_id"] for row in rows}) != len(rows):
        failures.append("plan_denominator_or_unique_run_ids")
    if set(responses) != {row["run_id"] for row in plan}:
        failures.append("response_plan_bijection")
    counts = Counter(row["status"] for row in rows)
    audit = {
        "experiment_id": "g6_counterfactual",
        "scope": "CF3 retry independent public-only mathematical audit",
        "plan_count": len(plan),
        "response_count": len(responses),
        "audit_count": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "decision_counts": dict(sorted(Counter(str(row["decision"]) for row in rows).items())),
        "failures": failures,
        "plan_sha256": sha256(args.plan),
        "public_sha256": sha256(args.public),
        "responses_sha256": sha256(args.responses),
        "private_oracle_loaded": False,
        "private_labels_used": False,
        "scientific_release_allowed": False,
        "verifier_source_sha256": verifier_sha256(),
    }
    args.out_audit.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    args.out_audit.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    args.out_summary.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
