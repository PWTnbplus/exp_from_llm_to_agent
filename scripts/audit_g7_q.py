#!/usr/bin/env python3
"""Independent read-only audit for G7 Q/final-decision records."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


DECISION = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}


def readl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def changes(items: list[dict]) -> set[tuple[str, str]]:
    return {(str(x.get("claim_id")), str(x.get("to_status"))) for x in items if isinstance(x, dict)}


def q_record_is_complete(q: object) -> bool:
    """Check only the frozen public Q record schema.

    The G7 design specifies Q.verdict and Q.reason as strings; it does not
    prescribe a PASS/OK enum.  A model's Q text is not treated as an external
    mathematical proof here.  Scientific consistency is still decided by the
    independent V/L/U labels and expected final decision below.
    """
    if not isinstance(q, dict):
        return False
    verdict = q.get("verdict")
    reason = q.get("reason")
    return (isinstance(verdict, str) and bool(verdict.strip())
            and isinstance(reason, str) and bool(reason.strip()))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--states", type=Path, nargs="+", required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--g6-oracle", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    plans = {x["run_id"]: x for x in readl(args.plan)}
    labels = {x["case_id"]: x for x in readl(args.labels)}
    oracle = {x["case_id"]: x for x in readl(args.g6_oracle)}
    states = {}
    for path in args.states:
        for row in readl(path):
            states[row["run_id"]] = row
    verifier_ref = "g7-q-label-consistency-audit:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out = []
    for run_id, plan in plans.items():
        state = states.get(run_id)
        label = labels[plan["case_id"]]
        expected = oracle[plan["case_id"]]["expected_decision"]
        if not state or state.get("status") != "completed":
            out.append({"run_id": run_id, "is_valid": False, "independent_verifier_ref": verifier_ref,
                        "reason": "missing_or_incomplete_state"})
            continue
        stages = state.get("stages") or {}
        q = stages.get("Q") or {}
        final_ok = state.get("final_decision") in DECISION and state.get("final_decision") == expected
        v_ok = (stages.get("V") or {}).get("verdict") == label["v"]["verdict"]
        l = stages.get("L") or {}
        l_ok = set(l.get("nodes", [])) == set(label["l"]["nodes"]) and {
            (x.get("from"), x.get("to")) for x in l.get("edges", []) if isinstance(x, dict)
        } == {(x.get("from"), x.get("to")) for x in label["l"]["edges"] if isinstance(x, dict)}
        u_ok = changes((stages.get("U") or {}).get("node_changes", [])) == changes(label["u"]["node_changes"])
        q_ok = q_record_is_complete(q)
        out.append({"run_id": run_id, "is_valid": bool(final_ok and v_ok and l_ok and u_ok and q_ok),
                    "independent_verifier_ref": verifier_ref,
                    "checks": {"final_decision": final_ok, "V": v_ok, "L": l_ok, "U": u_ok,
                               "Q": q_ok, "Q_record_complete": q_ok},
                    "expected_decision": expected, "observed_decision": state.get("final_decision"),
                    "q_verdict": q.get("verdict"),
                    "assessment_scope": "label_consistency_and_q_record_completeness;_not_external_proof"})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        for row in out:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"runs": len(out), "valid": sum(x["is_valid"] for x in out),
                      "invalid": sum(not x["is_valid"] for x in out), "verifier_ref": verifier_ref}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
