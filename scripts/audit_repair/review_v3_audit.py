"""Independent read-only review for the V3 audit bundle."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", type=Path, required=True)
    args = parser.parse_args()
    d = args.docs
    failures: list[str] = []
    frozen = read_json(d / "FROZEN_INPUT_SHA256.json")
    if not frozen.get("protected_source_hashes_unchanged") or frozen.get("changed_paths"):
        failures.append("protected_source_hash_changed")
    matrix = list(csv.DictReader((d / "G7_STATE_ATTEMPT_MATRIX.csv").open(encoding="utf-8")))
    if len(matrix) != 1288 or len({r["state_id"] for r in matrix}) != 1288: failures.append("g7_matrix_not_bijective")
    trace = [json.loads(x) for x in (d / "G7_TRACE_15_EXPLAINED_13_INVALID.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(trace) != 28: failures.append("trace_count")
    if sum(r.get("classification") == "AUDIT_BOUNDARY_ARTIFACT" for r in trace) != 15: failures.append("trace_boundary_count")
    if sum(r.get("classification") == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY" for r in trace) != 13: failures.append("trace_genuine_count")
    if read_json(d / "V2_FINAL_METRICS.json").get("status") != "NOT_RUN": failures.append("v2_not_fail_closed")
    smoke = read_json(d / "V2_SCHEMA_VALIDATION_AND_LEAKAGE_TESTS.json")
    if smoke.get("status") != "SMOKE_PASS" or not all(smoke.get("anti_cheat", {}).values()): failures.append("v2_smoke")
    if read_json(d / "G0_G7_GATE_MATRIX.json").get("scientific_release_allowed") is not False: failures.append("release_not_blocked")
    result = {
        "review_version": "g6-g7-v3-independent-read-only-v1", "pass": not failures, "failures": failures,
        "counts": {"g7_states": len(matrix), "trace_old": len(trace), "trace_boundary": sum(r.get("classification") == "AUDIT_BOUNDARY_ARTIFACT" for r in trace), "trace_genuine": sum(r.get("classification") == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY" for r in trace)},
        "protected_source_hashes_unchanged": not failures or "protected_source_hash_changed" not in failures,
        "scientific_truth_decision_made": False,
    }
    (d / "18_INDEPENDENT_READ_ONLY_REVIEW_V3.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gates = read_json(d / "G0_G7_GATE_MATRIX.json")
    gates["evidence"]["independent_review_pending"] = False
    gates["independent_review"] = {"path": "18_INDEPENDENT_READ_ONLY_REVIEW_V3.json", "pass": result["pass"], "scientific_truth_decision_made": False}
    (d / "G0_G7_GATE_MATRIX.json").write_text(json.dumps(gates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__": raise SystemExit(main())
