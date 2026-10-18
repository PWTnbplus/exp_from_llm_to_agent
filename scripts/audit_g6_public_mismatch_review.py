"""Independent read-only audit for the G6 public mismatch correction cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.audit_g6_cf3_public_boundary_review import SPECS
except ModuleNotFoundError:  # direct script entry point
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.audit_g6_cf3_public_boundary_review import SPECS


FORBIDDEN = ("private_oracle", "expected_decision", "correct_revised_claim", "hidden_true", "answer_key", "g7_vlu_private")
DECISIONS = {"MAINTAIN", "REVISE", "REJECT", "UNDETERMINED"}
REQUIRED = {"decision", "affected_claim_ids", "revised_claim", "supporting_evidence", "boundary_handling"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(forbidden(k) or forbidden(v) for k, v in value.items())
    if isinstance(value, list):
        return any(forbidden(v) for v in value)
    return isinstance(value, str) and any(term in value.casefold() for term in FORBIDDEN)


def token_hits(candidate: dict[str, Any], family: str) -> int:
    spec = SPECS[family]
    text = " ".join(str(candidate.get(key) or "") for key in ("revised_claim", "supporting_evidence", "boundary_handling")).casefold().replace(" ", "")
    return sum(str(token).casefold().replace(" ", "") in text for token in spec["tokens"])


def alignment(candidate: dict[str, Any], family: str) -> tuple[str, str, int]:
    spec = SPECS[family]
    decision = str(candidate.get("decision") or "").upper()
    hits = token_hits(candidate, family)
    if spec["outcome"] == "preserves_specific":
        ok = decision == "MAINTAIN" and hits >= 1
    elif spec["outcome"] == "degenerate_formula":
        ok = decision in {"REVISE", "REJECT"} and hits >= 2
    else:
        ok = decision in {"REVISE", "REJECT"} and hits >= 2
    return ("PUBLIC_ALIGNMENT" if ok else "PUBLIC_MISMATCH_REMAINS", spec["outcome"], hits)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-model-id", default="kimi-k2.5")
    args = parser.parse_args()
    plan_value = json.loads(args.plan.read_text(encoding="utf-8"))
    if isinstance(plan_value, dict) and isinstance(plan_value.get("selected_prior_run_ids"), list):
        plan_ids = set(plan_value["selected_prior_run_ids"])
        plan_count = int(plan_value.get("selected_count", len(plan_ids)))
    elif isinstance(plan_value, list):
        plan_ids = {row.get("run_id") for row in plan_value}
        plan_count = len(plan_value)
    else:
        raise ValueError("G6 review plan must be a summary or JSONL plan")
    records = read_jsonl(args.records)
    traces = read_jsonl(args.traces)
    failures: list[str] = []
    quality_issues: list[str] = []
    if plan_count != 43 or len(plan_ids) != 43:
        failures.append("plan_not_exactly_43_unique_prior_runs")
    if len(records) != plan_count or len({row.get("prior_run_id") for row in records}) != len(records):
        failures.append("record_plan_bijection")
    if not traces:
        failures.append("no_provider_traces")
    record_ids = {row.get("prior_run_id") for row in records}
    if plan_ids != record_ids:
        failures.append("prior_run_id_set_mismatch")
    alignment_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    valid = 0
    for row in records:
        prior_id = row.get("prior_run_id")
        family = str(row.get("family") or "")
        if family not in SPECS:
            failures.append(f"unknown_family:{prior_id}")
        if row.get("model_id") != args.expected_model_id:
            failures.append(f"record_model:{prior_id}")
        if row.get("private_labels_read") is not False or row.get("private_oracle_read") is not False:
            failures.append(f"private_flags:{prior_id}")
        candidate = row.get("candidate")
        error = row.get("validation_error")
        validation_counts[str(error or "none")] += 1
        if candidate is not None:
            if forbidden(candidate):
                failures.append(f"forbidden_candidate:{prior_id}")
            if set(candidate) != REQUIRED or candidate.get("decision") not in DECISIONS:
                quality_issues.append(f"candidate_schema:{prior_id}")
            elif not isinstance(candidate.get("affected_claim_ids"), list) or any(not isinstance(x, str) for x in candidate["affected_claim_ids"]):
                quality_issues.append(f"candidate_claim_ids:{prior_id}")
            elif not isinstance(candidate.get("supporting_evidence"), str) or not candidate["supporting_evidence"].strip():
                quality_issues.append(f"candidate_evidence:{prior_id}")
            elif not isinstance(candidate.get("boundary_handling"), str) or not candidate["boundary_handling"].strip():
                quality_issues.append(f"candidate_boundary:{prior_id}")
            elif not error and family in SPECS:
                valid += 1
                status, outcome, hits = alignment(candidate, family)
                alignment_counts[status] += 1
                row["public_alignment"] = status
                row["public_outcome"] = outcome
                row["public_witness_token_hits"] = hits
        trace_rows = [trace for trace in traces if trace.get("review_id") == row.get("review_id")]
        if not trace_rows:
            failures.append(f"missing_trace:{prior_id}")
        for trace in trace_rows:
            if trace.get("model") != args.expected_model_id:
                failures.append(f"trace_model:{prior_id}")
            if forbidden(trace.get("request")):
                failures.append(f"forbidden_request:{prior_id}")
    summary = {
        "schema_version": 1,
        "audit_version": "g6-public-mismatch-independent-v1",
        "plan_count": plan_count,
        "record_count": len(records),
        "trace_count": len(traces),
        "valid_candidate_count": valid,
        "public_alignment_counts": dict(sorted(alignment_counts.items())),
        "validation_error_counts": dict(sorted(validation_counts.items())),
        "candidate_quality_issues": quality_issues,
        "plan_sha256": sha256(args.plan),
        "records_sha256": sha256(args.records),
        "traces_sha256": sha256(args.traces),
        "private_labels_read": False,
        "private_oracle_read": False,
        "pooled_with_frozen_g6": False,
        "scientific_release_allowed": False,
        "failures": failures,
        "engineering_audit_pass": not failures and len(records) == plan_count and bool(traces),
        "interpretation": "A public alignment after corrective review is not a blinded oracle score and cannot erase the 43 historical mismatches.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
