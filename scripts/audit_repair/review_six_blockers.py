"""Independent read-only review of the six-blocker audit outputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts import audit_g7_trace_q_consistency as trace_audit


def readl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=Path, required=True)
    p.add_argument("--local", type=Path, required=True)
    p.add_argument("--g7-root", type=Path, required=True)
    args = p.parse_args()
    failures: list[str] = []
    manifest = json.loads((args.docs / "00_SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    before = {row["source_path"]: row["sha256"] for row in manifest["before"]["files"]}
    after = {row["source_path"]: row["sha256"] for row in manifest["after"]["files"]}
    if before != after or not manifest.get("protected_source_sha256_unchanged"):
        failures.append("protected_source_hash_changed")
    revision_rows = list(csv.DictReader((args.local / "02_G6_REVISION_ROOT_CAUSES.csv").open(encoding="utf-8")))
    if len(revision_rows) != 138 or len({row["run_id"] for row in revision_rows}) != 138:
        failures.append("g6_revision_denominator_not_bijective")
    state_rows = list(csv.DictReader((args.local / "06_G7_STATE_RESUME_MATRIX.csv").open(encoding="utf-8")))
    if len(state_rows) != 1288 or len({row["state_id"] for row in state_rows}) != 1288:
        failures.append("g7_state_denominator_not_bijective")
    trace_rows = list(csv.DictReader((args.local / "07_G7_28_TO_15_PLUS_13_TRACE_RECONCILIATION.csv").open(encoding="utf-8")))
    if len(trace_rows) != 28:
        failures.append(f"trace_old_count:{len(trace_rows)}")
    if sum(row["classification"] == "AUDIT_BOUNDARY_ARTIFACT" for row in trace_rows) != 15:
        failures.append("trace_boundary_count_not_15")
    if sum(row["classification"] == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY" for row in trace_rows) != 13:
        failures.append("trace_genuine_count_not_13")
    incidents = readl(args.local / "08_G7_13_TRACE_INCIDENTS.jsonl")
    if len(incidents) != 13:
        failures.append("trace_incident_rows_not_13")
    q_rows = readl(args.local / "09_G7_Q_INDEPENDENT_AUDIT.jsonl")
    if len(q_rows) != 1288:
        failures.append("q_denominator_not_1288")
    if any(row.get("status") == "PASS" and not row.get("check_provenance_valid") for row in q_rows):
        failures.append("q_pass_without_provenance")
    verifier_source = (Path(__file__).parent / "verify_q.py").read_text(encoding="utf-8")
    if "expected_decision" in verifier_source or "private_oracle" in verifier_source:
        failures.append("q_verifier_contains_forbidden_truth_source")
    lu = json.loads((args.docs / "14_FINAL_GATES.json").read_text(encoding="utf-8"))
    if lu.get("scientific_release_allowed") is not False or lu.get("release") != "BLOCKED":
        failures.append("release_gate_not_fail_closed")
    result = {
        "review_version": "six-blocker-independent-read-only-v1",
        "pass": not failures,
        "failures": failures,
        "counts": {"g6_revision": len(revision_rows), "g7_states": len(state_rows), "trace_old": len(trace_rows), "trace_boundary": sum(row["classification"] == "AUDIT_BOUNDARY_ARTIFACT" for row in trace_rows), "trace_genuine": sum(row["classification"] == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY" for row in trace_rows), "trace_incidents": len(incidents), "q": len(q_rows)},
        "protected_source_hashes_unchanged": not failures or "protected_source_hash_changed" not in failures,
        "scientific_truth_decision_made": False,
    }
    (args.docs / "17_INDEPENDENT_READ_ONLY_REVIEW.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
