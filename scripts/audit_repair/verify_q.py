"""Independent post-hoc Q verifier for G7.

The CLI accepts only the frozen public case, plan, state, and trace data.  It
does not accept labels, expected decisions, or a private oracle.  Free-form
model Q prose is retained but is not promoted to a mathematical proof unless
the narrow independent verifier can parse and replay it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .math_verifier import verify_candidate_claim


def readl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_state(state: dict[str, Any], plan: dict[str, Any], public: dict[str, Any],
                 *, trace_path: Path | None = None) -> dict[str, Any]:
    q = ((state.get("stages") or {}).get("Q") or {})
    model_claim = q.get("reason") if isinstance(q, dict) else None
    base = {
        "state_id": plan.get("run_id"),
        "attempt_id": state.get("run_id"),
        "q_claimed_by_model": q.get("verdict") if isinstance(q, dict) else None,
        "model_claimed_check": model_claim,
        "actual_check_executed": False,
        "check_provenance_valid": False,
        "candidate_claim_ref": None,
        "evidence_grade": None,
        "status": "NOT_SCORED",
        "final_Y_status": None,
        "verifier_ref": "scripts/audit_repair/verify_q.py",
        "verifier_code_sha256": sha256(Path(__file__)),
        "replay_command": None,
        "trace_sha256": sha256(trace_path) if trace_path and trace_path.is_file() else None,
        "reason_code": "MODEL_Q_FREE_TEXT_NO_REPLAYABLE_CLAIM",
    }
    if state.get("status") != "completed":
        base["status"] = "INELIGIBLE"
        base["reason_code"] = "STATE_NOT_COMPLETED"
        return base
    if not isinstance(q, dict) or not isinstance(model_claim, str) or not model_claim.strip():
        base["status"] = "NOT_SCORED"
        base["reason_code"] = "CLAIM_UNPARSABLE"
        return base
    # A Q reason is evidence text, not automatically a candidate mathematical
    # claim.  The explicit marker is required before the narrow verifier is
    # allowed to parse it; the production run contains no such marker.
    marker = "candidate_claim:"
    if marker not in model_claim.casefold():
        return base
    claim = model_claim.split(":", 1)[1].strip()
    verdict = verify_candidate_claim(
        cf_type=str(plan.get("cf_type", "")), claim=claim,
        quantifier=str(public.get("quantifier", "")),
        public_problem=str((public.get("model_visible") or {}).get("original_problem", "")),
    )
    base.update({
        "actual_check_executed": True,
        "check_provenance_valid": verdict.status in {"PASS", "FAIL"},
        "candidate_claim_ref": "model_q_reason:candidate_claim",
        "evidence_grade": verdict.grade,
        "status": verdict.status,
        "reason_code": verdict.reason_code,
        "proof_or_counterexample": verdict.evidence,
        "final_Y_status": state.get("final_decision"),
    })
    return base


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--states", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--trace-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    plans = {row["run_id"]: row for row in readl(args.plan)}
    public = {row["case_id"]: row for row in readl(args.public)}
    rows = []
    for state in readl(args.states):
        plan = plans.get(state.get("run_id"), {})
        trace_ref = state.get("trace_ref")
        trace = args.trace_root / Path(str(trace_ref).replace("\\", "/")) if trace_ref else None
        rows.append(verify_state(state, plan, public.get(plan.get("case_id"), {}), trace_path=trace))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    from collections import Counter
    print(json.dumps({"rows": len(rows), "status_counts": Counter(row["status"] for row in rows),
                      "verifier_sha256": sha256(Path(__file__))}, ensure_ascii=False, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
