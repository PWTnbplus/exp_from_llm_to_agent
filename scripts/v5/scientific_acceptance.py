"""Build a fail-closed G0-G7 scientific acceptance matrix.

This is a read-only arbiter over persisted evidence.  It does not call a
provider, read a private oracle, alter a denominator, or turn engineering
checks into scientific results.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--gates", type=Path, default=Path("docs/state/gates.json"))
    parser.add_argument("--issues", type=Path, default=Path("docs/state/issues.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pack = args.pack
    gates = load(args.gates)
    issues = load(args.issues)
    summary = load(pack / "BUILD_SUMMARY.json")
    independent = load(pack / "INDEPENDENT_READ_ONLY_REVIEW.json")
    q_manifest = load(pack / "Q92_BLIND_PACK_MANIFEST.json")
    lu_prereg = load(pack / "LU_U_FORMAL_PREREG.json")
    remote = load(pack / "REMOTE_SHA_AND_PROVENANCE_REVIEW.json")
    g7_decision = (pack / "G7_REANALYSIS_PROTOCOL_DECISION.md").read_text(encoding="utf-8")

    gate_rows = []
    for gate in ("G0", "G1", "G2", "G3", "G4", "G5"):
        source = gates["gates"][gate]
        gate_rows.append(
            {
                "gate": gate,
                "engineering_status": source["status"],
                "scientific_acceptance": (
                    "PARTIAL_NOT_RELEASE_READY"
                    if gate == "G0"
                    else "PRECONDITION_PASS_NOT_SCIENTIFIC_RESULT"
                ),
                "scope": source["scope"],
                "reason": (
                    "Pinned simulator provenance/licensing is present, but official numeric evaluator, "
                    "immutable model identity, and provider billing are not all verified."
                    if gate == "G0"
                    else "The gate is an engineering/protocol precondition and does not establish law rediscovery or Agent superiority."
                ),
            }
        )

    g6 = summary["g6"]
    gate_rows.append(
        {
            "gate": "G6",
            "engineering_status": "PASS_INDEPENDENT_REVIEW",
            "scientific_acceptance": "BLOCKED",
            "scope": "formal_scientific_release",
            "reason": "External mathematical/domain review and formal statistical release conditions are incomplete.",
            "evidence": {
                "input_rows": g6["input_rows"],
                "case_level_rows": g6["case_level_rows"],
                "proven_equivalent": g6["verdict_counts"].get("PROVEN_EQUIVALENT", 0),
                "inconclusive_or_not_scorable": g6["verdict_counts"].get("INCONCLUSIVE_OR_NOT_SCORABLE", 0),
                "formal_552_denominator_modified": g6["formal_552_denominator_modified"],
                "external_domain_review_complete": g6["external_domain_review_complete"],
            },
        }
    )

    g7 = summary["g7"]
    gate_rows.append(
        {
            "gate": "G7",
            "engineering_status": "PASS_INDEPENDENT_REVIEW",
            "scientific_acceptance": "BLOCKED",
            "scope": "formal_scientific_release",
            "reason": "Provider-valid Q coverage, immutable route/weight identity, and protocol-approved denominator reanalysis are incomplete.",
            "evidence": {
                "frozen_rows": g7["historical_rows"],
                "recovery_rows": g7["recovery_rows"],
                "historical_genuine_failures_retained": g7["historical_genuine_lifecycle_failures_retained"],
                "recovery_trace_backed": g7["recovery_trace_backed"],
                "denominator_changed": g7["denominator_changed"],
                "reanalysis_protocol_approved": "NOT_APPROVED_FOR_FORMAL_DENOMINATOR_CHANGE" not in g7_decision,
            },
        }
    )

    unresolved = [i for i in issues["issues"] if i["status"] != "VERIFIED"]
    blocker_ids = [
        i["id"]
        for i in unresolved
        if i["id"]
        in {
            "ISSUE-000000000002",
            "ISSUE-000000000003",
            "ISSUE-000000000004",
            "ISSUE-ff97c7c89112",
            "ISSUE-1f8c2b6a4d90",
            "ISSUE-3d7a9c1e5b20",
        }
    ]

    result = {
        "acceptance_version": "g0-g7-scientific-acceptance-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "provider_calls_in_acceptance": 0,
        "gate_rows": gate_rows,
        "summary": {
            "engineering_or_protocol_pass_count": sum(row["engineering_status"] == "PASS" for row in gate_rows[:6]),
            "formal_scientific_gate_pass_count": 0,
            "full_scientific_acceptance_count": 0,
            "scientific_release_allowed": False,
            "interpretation": "Six engineering/precondition gates have evidence; no full G0-G7 scientific release claim is allowed while G6/G7 remain blocked.",
        },
        "independent_review_pass": independent["engineering_review_pass"],
        "q92": {
            "case_count": q_manifest["case_count"],
            "domain_grade_review_complete": q_manifest["domain_grade_review_complete"],
        },
        "lu_u": {
            "status": lu_prereg["status"],
            "u_eligible_count": summary["lu_u"]["u_eligible_count"],
            "validated_causal_contrast_count": summary["lu_u"]["validated_causal_contrast_count"],
        },
        "provider_and_provenance": {
            "official_billing_verified": summary["provider"]["official_billing_verified"],
            "immutable_route_or_weight_verified": summary["provider"]["immutable_route_or_weight_verified"],
            "remote_sha_verified": remote["remote_sha_verified"],
        },
        "unresolved_scientific_blocker_ids": sorted(blocker_ids),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
