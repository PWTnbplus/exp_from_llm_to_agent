"""Independent public-only audit for a Q-v2 cohort, including fixed format retries."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.v3.q_v2 import sha256_json, verify_q_record


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contains_private(value: Any) -> bool:
    terms = ("expected_decision", "correct_revised_claim", "private_oracle", "oracle_reason", "g7_vlu_private", "answer_key")
    if isinstance(value, dict):
        return any(contains_private(key) or contains_private(child) for key, child in value.items())
    if isinstance(value, list):
        return any(contains_private(child) for child in value)
    if isinstance(value, str):
        folded = value.casefold()
        return any(term in folded for term in terms)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--proof-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-model-id", default="kimi-k2.5")
    args = parser.parse_args()

    records = read_jsonl(args.records)
    traces = read_jsonl(args.traces)
    failures: list[str] = []
    stored_counts = Counter(str(row.get("independent_q", {}).get("status")) for row in records)
    recomputed_counts: Counter[str] = Counter()
    proof_hashes_valid = True
    for record in records:
        independent = record.get("independent_q") or {}
        recomputed = verify_q_record(record)
        recomputed_counts[str(recomputed.get("status"))] += 1
        if recomputed.get("status") != independent.get("status") or recomputed.get("reason_code") != independent.get("reason_code"):
            failures.append(f"stored_recomputed_mismatch:{record.get('case_id')}")
        candidate = record.get("candidate")
        if record.get("q_evidence", {}).get("verifier_input_hash") != sha256_json(candidate):
            failures.append(f"input_hash:{record.get('case_id')}")
        proof_ref = record.get("q_evidence", {}).get("verifier_output_ref")
        proof_ref_text = str(proof_ref)
        # The runner stores refs relative to the cohort root (proofs/x.json),
        # while this audit receives the proof directory for containment.  Do
        # not silently turn that into proofs/proofs/x.json.
        proof_path = args.proof_dir.parent / proof_ref_text if proof_ref_text.startswith("proofs/") else args.proof_dir / proof_ref_text
        try:
            proof_path.resolve().relative_to(args.proof_dir.resolve())
        except ValueError:
            failures.append(f"proof_ref_outside_dir:{record.get('case_id')}")
            proof_path = args.proof_dir / "__invalid_ref__"
        if not proof_path.is_file() or record.get("q_evidence", {}).get("verifier_output_sha256") != sha256(proof_path):
            proof_hashes_valid = False
        if contains_private(record.get("candidate")):
            failures.append(f"private_candidate:{record.get('case_id')}")
    trace_case_ids = {trace.get("cohort_case_id") for trace in traces}
    models = {str(trace.get("model")) for trace in traces}
    if models != {args.expected_model_id}:
        failures.append(f"models:{sorted(models)}")
    if len(trace_case_ids) != len(records) or not trace_case_ids.issubset({row.get("case_id") for row in records}):
        failures.append("trace_case_bijection")
    if any(contains_private(trace.get("request")) for trace in traces):
        failures.append("private_trace_request")
    summary = {
        "audit_version": "q-v2-independent-rereview-with-format-retry-v1",
        "records": len(records),
        "unique_case_ids": len({row.get("case_id") for row in records}),
        "traces": len(traces),
        "unique_trace_cases": len(trace_case_ids),
        "format_retry_records": sum(row.get("format_retry_used") is True for row in records),
        "provider_attempts_total": sum(int(row.get("provider_attempts", 0)) for row in records),
        "models": sorted(models),
        "stored_counts": dict(sorted(stored_counts.items())),
        "recomputed_counts": dict(sorted(recomputed_counts.items())),
        "stored_matches_recomputed": stored_counts == recomputed_counts,
        "proof_hashes_valid": proof_hashes_valid,
        "provider_successful_records": sum(bool(row.get("provider_usage")) for row in records),
        "parse_error_records": sum(bool(row.get("parse_errors")) for row in records),
        "private_labels_read": False,
        "answer_key_read": False,
        "pooling_with_frozen_g7": False,
        "scientific_release_allowed": False,
        "records_sha256": sha256(args.records),
        "traces_sha256": sha256(args.traces),
        "failures": failures,
        "engineering_audit_pass": not failures and proof_hashes_valid and stored_counts == recomputed_counts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["engineering_audit_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
