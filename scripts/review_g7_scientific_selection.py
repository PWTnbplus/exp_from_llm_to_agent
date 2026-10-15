#!/usr/bin/env python3
"""Freeze a manually reviewed, public-only V candidate for G8.

This is a derived handoff.  The original G7 handoff remains immutable and is
not silently upgraded.  No private oracle or answer key is loaded here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--g7-root", type=Path, required=True)
    p.add_argument("--trace-review", type=Path, required=True)
    p.add_argument("--verifier", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    root = args.g7_root.resolve()
    trace_review = json.loads(args.trace_review.read_text(encoding="utf-8"))
    public = rows(root / "g7_public_cases.jsonl")
    checkpoints = rows(args.trace_review.parent / "g8_public_checkpoints.jsonl")
    by_case = {row["case_id"]: row for row in public}
    by_pair = {(row["case_id"], row["group_id"]): row for row in checkpoints}
    # These examples are selected from public interventions, not from the
    # hidden labels.  The first two expose parameter/domain checks; the latter
    # two are cosmetic counterexamples where the mechanism should be neutral.
    supporting = [
        ("G6F-TB-L1-002-CF1", "G4"),  # logistic r changed to -0.5
        ("G6F-TC-L1-001-CF1", "G4"),  # decay k changed to -0.4
    ]
    counterexamples = [
        ("G6F-TB-L1-001-CF2", "G3"),  # pure state-variable rename
        ("G6F-TC-L1-004-CF2", "G4"),  # pure Arrhenius variable rename
    ]
    errors: list[str] = []
    for case_id, group in supporting + counterexamples:
        if case_id not in by_case:
            errors.append(f"missing public case {case_id}")
        if (case_id, group) not in by_pair:
            errors.append(f"missing completed public checkpoint {case_id}/{group}")
    if trace_review.get("status") != "REAL_TRACE_AUDITED":
        errors.append("source-only trace review is not REAL_TRACE_AUDITED")
    if errors:
        raise SystemExit("selection review failed: " + "; ".join(errors))

    source_hashes = [
        sha(root / "g7_public_cases.jsonl"),
        sha(root / "g7_checkpoints.jsonl"),
        sha(root / "g7_score_report.json"),
        sha(root / "g7_vlu_oracle_audit.json"),
        sha(args.trace_review),
        sha(args.trace_review.parent / "g8_public_checkpoints.jsonl"),
    ]
    evidence_refs = [
        f"checkpoint:{by_pair[key]['checkpoint_id']}" for key in supporting + counterexamples
    ] + [
        "g7_score_report:diagnostic_paired_effects.V_ONLY_minus_D0",
        "g7_vlu_oracle_audit:edge_count_distribution",
    ]
    handoff = {
        "experiment_id": "g7_failure_localization",
        "g8_interface_version": "g7-to-g8-v1-reviewed-public-v-20261015",
        "selection": "GO",
        "selection_scope": "G8 pilot and preregistered continuation only; not a claim that G7 truth/Q gates are resolved",
        "source_g7_evidence_status": "REAL_TRACE_AUDITED",
        "review_method": "manual public-scientific review plus independent read-only trace audit; no private oracle or answer key loaded",
        "mechanisms": [{
            "mechanism_id": "V",
            "failure_mode": "The workflow can fail to re-evaluate a public mathematical/domain consequence of the intervention before committing to a final decision.",
            "supporting_case_ids": [case_id for case_id, _ in supporting],
            "counterexample_case_ids": [case_id for case_id, _ in counterexamples],
            "g7_evidence_refs": evidence_refs,
            "planned_g8_controls": [
                "M_real is a public-only deterministic equation check and emits calculations, never a decision label",
                "M_sham preserves the V schema but has no semantic calculation payload",
                "M_off prevents the mechanism state from being read downstream and emits MECHANISM_DISABLED",
                "generic extra thinking receives no new evidence and is separately logged",
            ],
            "operational_definition": "At the frozen public checkpoint, invoke g8_public_v_verifier.verify_public_case(model_visible). Accept M_real only when its schema, public-input hash, non-oracle quality flags, and bounded numeric checks pass; expose only that result to the model before final decision.",
            "falsification": "V is not supported if B_G3_REAL_M does not improve the preregistered all-planned completion contrast over A_G3_BASE and C_G3_SHAM_M, or if it increases C-to-W beyond the safety gate; any result with failed mechanism-event or budget audit is invalid rather than evidence.",
            "verifier_hashes": [sha(args.verifier)],
            "source_hashes": source_hashes,
        }],
        "g7_score_sha256": sha(root / "g7_score_report.json"),
        "g7_trace_review_sha256": sha(args.trace_review),
        "caveats": [
            "G7 retained 31 terminal checkpoint provider errors and 1285/1288 Q rows were independently invalid; G8 must keep this provenance visible.",
            "The provider metadata is an identity record, not an immutable weight fingerprint; billing remains locally recorded rather than externally reconciled.",
            "This GO selects a pilot mechanism for execution and does not convert G7 diagnostic labels into mathematical truth.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selection": handoff["selection"], "mechanism_ids": ["V"],
                      "supporting_cases": handoff["mechanisms"][0]["supporting_case_ids"],
                      "counterexamples": handoff["mechanisms"][0]["counterexample_case_ids"],
                      "source_hashes": len(source_hashes)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
