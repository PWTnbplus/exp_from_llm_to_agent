"""Public-only deterministic boundary review for the G6 CF3 retry.

This is a second review layer for the 23 published model families.  It derives
the boundary consequence from the public problem/intervention and checks
whether the model's revision action acknowledges that consequence.  It never
loads the private oracle or private labels and does not claim oracle accuracy.
The result is therefore stronger coverage evidence, not an automatic release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# These witnesses are derived from the public original problem and its CF3
# intervention.  They deliberately describe mathematical boundary behavior,
# not the private protocol label or oracle decision.
SPECS: dict[str, dict[str, Any]] = {
    "G6F-TC-L1-001": {"parameter": "k", "boundary": "k=0", "outcome": "invalidates", "witness": "dA/dt=0, A(t)=A0; half-life is undefined/infinite", "tokens": ("k=0", "half", "undefined")},
    "G6F-TC-L1-002": {"parameter": "k", "boundary": "k=0", "outcome": "invalidates", "witness": "dA/dt=0, A(t)=A0; second-order half-life is undefined/infinite", "tokens": ("k=0", "half", "undefined")},
    "G6F-TC-L1-003": {"parameter": "k", "boundary": "k=0", "outcome": "invalidates", "witness": "dA/dt=0, A(t)=A0; complete depletion never occurs", "tokens": ("k=0", "undefined", "constant")},
    "G6F-TC-L1-004": {"parameter": "Ea", "boundary": "Ea=0", "outcome": "invalidates", "witness": "Arrhenius ratio exp(0)=1, not the original 6.186749", "tokens": ("ea=0", "ratio", "1")},
    "G6F-TC-L1-005": {"parameter": "T", "boundary": "T=0", "outcome": "preserves_specific", "witness": "The public numerical claim uses T=298; the boundary T=0 is singular and must remain a domain caveat", "tokens": ("t=0", "298", "unchanged")},
    "G6F-TC-L1-006": {"parameter": "DeltaH", "boundary": "DeltaH=0", "outcome": "invalidates", "witness": "van't Hoff integration gives K2=K1=2 when DeltaH=0", "tokens": ("0", "k2", "2")},
    "G6F-TC-L1-007": {"parameter": "epsilon_over_RT", "boundary": "epsilon_over_RT=0", "outcome": "invalidates", "witness": "Z=2 and excited-state probability=1/2 at the boundary", "tokens": ("0", "z=2", "0.5")},
    "G6F-TC-L1-008": {"parameter": "x", "boundary": "x=0", "outcome": "preserves_specific", "witness": "C_V/R=0 at x=0; the original x=1.5 value and x-to-infinity limit remain defined", "tokens": ("x=0", "0", "unchanged")},
    "G6F-TC-L1-009": {"parameter": "kB", "boundary": "kB=0", "outcome": "degenerate_formula", "witness": "B/C=0 and fraction_to_B=0 with kC=0.2; the reaction branch is degenerate", "tokens": ("kb=0", "0", "degenerate")},
    "G6F-TC-L1-010": {"parameter": "k", "boundary": "k=0", "outcome": "invalidates", "witness": "k_obs=0 and the half-life is undefined/infinite", "tokens": ("k=0", "k_obs", "half")},
    "G6F-TC-L1-011": {"parameter": "ratio", "boundary": "ratio=0", "outcome": "preserves_specific", "witness": "log10(0) is outside the formula domain, but the public claim evaluates ratio=3.2", "tokens": ("ratio=0", "3.2", "undefined")},
    "G6F-TC-L1-012": {"parameter": "Vmax", "boundary": "Vmax=0", "outcome": "invalidates", "witness": "v=0 and v/Vmax at S=Km is undefined at Vmax=0", "tokens": ("vmax=0", "v=0", "undefined")},
    "G6F-TB-L1-001": {"parameter": "r", "boundary": "r=0", "outcome": "invalidates", "witness": "N(t)=N0 is constant and doubling time is undefined/infinite", "tokens": ("r=0", "constant", "doubling")},
    "G6F-TB-L1-002": {"parameter": "r", "boundary": "r=0", "outcome": "preserves_specific", "witness": "N*=0 and N*=K remain equilibria; stability is non-hyperbolic and is not asserted by the original claim", "tokens": ("r=0", "equilibrium", "stability")},
    "G6F-TB-L1-003": {"parameter": "h", "boundary": "h=0", "outcome": "invalidates", "witness": "roots are 0 and K, so there are not two positive equilibria", "tokens": ("h=0", "root", "positive")},
    "G6F-TB-L1-004": {"parameter": "beta", "boundary": "beta=0", "outcome": "invalidates", "witness": "R0=0 and infection decays; the disease-free equilibrium is locally stable", "tokens": ("beta=0", "r0", "stable")},
    "G6F-TB-L1-005": {"parameter": "Vmax", "boundary": "Vmax=0", "outcome": "invalidates", "witness": "v=0 at the boundary; the original specific v=0.4897959 is not retained", "tokens": ("vmax=0", "v=0", "0.489")},
    "G6F-TB-L1-006": {"parameter": "K", "boundary": "K=0", "outcome": "invalidates", "witness": "theta=1 for S=1, and theta is 0/0 when S=K=0", "tokens": ("k=0", "theta", "undefined")},
    "G6F-TB-L1-007": {"parameter": "a", "boundary": "a=0", "outcome": "invalidates", "witness": "y*=a/b=0, so no positive coexistence equilibrium exists", "tokens": ("a=0", "y", "positive")},
    "G6F-TB-L1-008": {"parameter": "alpha", "boundary": "alpha=0", "outcome": "preserves_specific", "witness": "P*=0 at the boundary; the public alpha=3 calculation remains P*=6 and tau=2", "tokens": ("alpha=0", "p*=0", "unchanged")},
    "G6F-TB-L1-009": {"parameter": "kon", "boundary": "kon=0", "outcome": "degenerate_formula", "witness": "p_on=0 and p_off=1; the two-state probability constraint remains valid", "tokens": ("kon=0", "p_on", "p_off")},
    "G6F-TB-L1-011": {"parameter": "D", "boundary": "D=0", "outcome": "preserves_specific", "witness": "mu=0.8333>0, so the public growth conclusion remains true", "tokens": ("d=0", "0.833", "growth")},
    "G6F-TB-L1-012": {"parameter": "resident_prey", "boundary": "resident_prey=0", "outcome": "invalidates", "witness": "invasion growth becomes -c+d*0=-1, not the original +1", "tokens": ("0", "growth", "-1")},
}


def folded(value: Any) -> str:
    return str(value or "").casefold().replace(" ", "")


def review_row(plan_row: dict[str, Any], public_row: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    family = str(plan_row["case_id"]).rsplit("-CF3", 1)[0]
    spec = SPECS.get(family)
    if spec is None:
        return {"run_id": plan_row["run_id"], "case_id": plan_row["case_id"], "family": family, "status": "NOT_SCORED", "reason": "UNDECLARED_PUBLIC_FAMILY"}
    visible = public_row.get("model_visible") or {}
    intervention = folded(visible.get("intervention_statement"))
    if folded(spec["boundary"]) not in intervention and folded(spec["parameter"]) not in intervention:
        return {"run_id": plan_row["run_id"], "case_id": plan_row["case_id"], "family": family, "status": "NOT_SCORED", "reason": "PUBLIC_INTERVENTION_MISMATCH"}
    decision = str(response.get("decision") or "").upper()
    claim_text = folded(response.get("revised_claim"))
    evidence_text = folded(response.get("supporting_evidence"))
    observed = claim_text + " " + evidence_text
    token_hits = sum(token.casefold().replace(" ", "") in observed for token in spec["tokens"])
    if spec["outcome"] == "preserves_specific":
        accepted = decision == "MAINTAIN" and token_hits >= 1
        reason = "PUBLIC_SPECIFIC_CLAIM_PRESERVED" if accepted else "MODEL_DID_NOT_ACKNOWLEDGE_PUBLIC_DOMAIN_SCOPE"
    elif spec["outcome"] == "degenerate_formula":
        accepted = decision in {"REVISE", "REJECT"} and token_hits >= 2
        reason = "PUBLIC_DEGENERATE_BOUNDARY_ACKNOWLEDGED" if accepted else "MODEL_DID_NOT_ACKNOWLEDGE_DEGENERACY"
    else:
        accepted = decision in {"REVISE", "REJECT"} and token_hits >= 2
        reason = "PUBLIC_BOUNDARY_COUNTEREXAMPLE_ACKNOWLEDGED" if accepted else "MODEL_ACTION_OR_EVIDENCE_CONTRADICTS_PUBLIC_WITNESS"
    return {
        "run_id": plan_row["run_id"],
        "case_id": plan_row["case_id"],
        "family": family,
        "model_decision": decision,
        "public_outcome": spec["outcome"],
        "boundary": spec["boundary"],
        "witness": spec["witness"],
        "token_hits": token_hits,
        "status": "PASS" if accepted else "FAIL",
        "reason": reason,
        "independent_of_private_oracle": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--out-audit", type=Path, required=True)
    parser.add_argument("--out-summary", type=Path, required=True)
    args = parser.parse_args()
    plan = read_jsonl(args.plan)
    public_rows = {row["case_id"]: row for row in read_jsonl(args.public)}
    responses = {row["run_id"]: row for row in read_jsonl(args.responses)}
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for plan_row in plan:
        response = responses.get(plan_row["run_id"], {})
        public = public_rows.get(plan_row["case_id"], {})
        if not response:
            failures.append(f"missing_response:{plan_row['run_id']}")
        rows.append(review_row(plan_row, public, response))
    families = {row["family"] for row in rows}
    if families != set(SPECS):
        failures.append("public_family_set_mismatch")
    if set(responses) != {row["run_id"] for row in plan}:
        failures.append("response_plan_bijection")
    counts = Counter(row["status"] for row in rows)
    result = {
        "schema_version": 1,
        "audit_version": "g6-cf3-public-boundary-review-v2",
        "plan_count": len(plan),
        "response_count": len(responses),
        "review_count": len(rows),
        "public_family_count": len(families),
        "status_counts": dict(sorted(counts.items())),
        "public_outcome_counts": dict(sorted(Counter(str(row.get("public_outcome")) for row in rows).items())),
        "failures": failures,
        "plan_sha256": sha256(args.plan),
        "public_sha256": sha256(args.public),
        "responses_sha256": sha256(args.responses),
        "private_oracle_loaded": False,
        "private_labels_used": False,
        "scientific_release_allowed": False,
        "interpretation": "Public boundary witnesses provide independent coverage and do not replace a blinded domain reviewer or the frozen oracle denominator.",
    }
    args.out_audit.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    args.out_audit.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    args.out_summary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
