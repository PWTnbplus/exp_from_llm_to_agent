#!/usr/bin/env python3
"""Independent, read-only audit for formal G8 output.

This audit deliberately does not load a private oracle.  It checks only the
frozen plan, result envelopes, public-visible traces, mechanism event
contracts, resource limits, and the public structure needed by the separate
Q/process audit files consumed by the G8 scorer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "expected_decision",
    "correct_revised_claim",
    "oracle_reason",
    "private_oracle",
    "V_true",
    "L_true_impacted_nodes",
    "U_true_node_changes",
    "ground_truth",
    "source_g6_oracle",
}
DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in values), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN:
                found.append(child_path)
            found.extend(forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(forbidden_paths(child, f"{path}[{i}]"))
    return found


def required_events(arm: str) -> set[str]:
    if arm in {"B_G3_REAL_M", "E_G4_PLUS_M"}:
        return {"MECHANISM_INVOKED", "MECHANISM_OUTPUT_ACCEPTED"}
    if arm == "C_G3_SHAM_M":
        return {"SHAM_MECHANISM_INVOKED", "SHAM_PAYLOAD_MATCHED"}
    if arm == "D_G3_EXTRA_THINK":
        return {"EXTRA_THINK_APPLIED"}
    if arm == "F_G4_MINUS_M":
        return {"MECHANISM_DISABLED"}
    return set()


def public_trace(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response") or {}
    trace = response.get("model_visible_trace")
    return trace if isinstance(trace, dict) else {}


def response_events(result: dict[str, Any]) -> list[dict[str, Any]]:
    response = result.get("response") or {}
    events = response.get("events")
    return events if isinstance(events, list) else []


def event_types(result: dict[str, Any]) -> set[str]:
    return {e.get("event_type") for e in response_events(result) if isinstance(e, dict)}


def independently_check_result(row: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    reasons: list[str] = []
    if not result:
        return {"run_id": row["run_id"], "status": "MISSING", "checks": {"result_present": False}, "reasons": ["result.json missing"]}

    response = result.get("response") or {}
    trace = public_trace(result)
    status = result.get("execution_status", "MISSING")
    checks["result_present"] = True
    checks["run_id_matches"] = result.get("run_id") == row.get("run_id")
    checks["plan_row_hash_present"] = bool(result.get("plan_row_hash"))
    checks["not_mock"] = result.get("is_mock") is not True and row.get("is_mock") is not True
    checks["public_only"] = response.get("public_only") is True and trace.get("public_only") is True
    checks["budget_enforced"] = response.get("budget_enforced") is True
    checks["snapshot_matches"] = response.get("actual_model_snapshot") == row.get("model_snapshot")
    checks["forbidden_absent"] = not forbidden_paths(trace)
    checks["mechanism_id_matches"] = trace.get("mechanism_id") in (None, row.get("mechanism_id"))
    observed = event_types(result)
    required = required_events(row.get("arm_id", ""))
    checks["required_events"] = status != "PASS" or required.issubset(observed)
    if required and status == "PASS" and not required.issubset(observed):
        reasons.append(f"missing required events: {sorted(required - observed)}")

    usage = response.get("usage") or {}
    limits = row.get("limits") or {}
    checks["usage_within_limits"] = all(
        usage.get(key) is not None and float(usage.get(key)) <= float(limits[key])
        for key in ("total_tokens", "model_calls", "tool_calls", "cost_usd")
        if key in limits
    ) if status == "PASS" else True
    checks["completed_response"] = status != "PASS" or (response.get("status") == "COMPLETED" and response.get("decision") in DECISIONS)
    if status == "PASS" and not checks["completed_response"]:
        reasons.append("PASS result does not contain a completed decision response")
    if not checks["snapshot_matches"]:
        reasons.append("actual model snapshot differs from frozen plan")
    if not checks["forbidden_absent"]:
        reasons.append("forbidden/private key found in model-visible trace")
    if status == "TECHNICAL_FAILURE":
        reasons.append("provider/adapter technical failure retained as ITT failure")
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "run_id": row["run_id"],
        "case_id": row.get("case_id"),
        "arm_id": row.get("arm_id"),
        "execution_status": status,
        "status": "PASS" if not failed_checks else "AUDIT_FAILURE",
        "checks": checks,
        "failed_checks": failed_checks,
        "observed_events": sorted(observed),
        "required_events": sorted(required),
        "reasons": reasons,
    }


def make_q_audit(row: dict[str, Any], result: dict[str, Any] | None, verifier_hash: str) -> dict[str, Any] | None:
    if not result:
        return None
    response = result.get("response") or {}
    if response.get("decision") != "REVISE":
        return None
    revised = response.get("revised_claim")
    events = event_types(result)
    trace = public_trace(result)
    evidence = response.get("supporting_evidence")
    passed = bool(
        result.get("execution_status") == "PASS"
        and response.get("status") == "COMPLETED"
        and isinstance(revised, str)
        and bool(revised.strip())
        and bool(evidence)
        and "MODEL_REQUEST" in events
        and "MODEL_RESPONSE" in events
        and response.get("public_only") is True
        and trace.get("public_only") is True
        and not forbidden_paths(trace)
    )
    return {
        "run_id": row["run_id"],
        "passed": passed,
        "evidence_ref": f"{row['run_id']}/result.json#independent_public_trace",
        "verifier_hash": verifier_hash,
        "claim_sha256": json_hash(revised),
        "audit_basis": "independent structural audit of public trace; no private oracle or expected label loaded",
    }


def make_process_audit(row: dict[str, Any], result: dict[str, Any] | None, review: dict[str, Any] | None) -> dict[str, Any]:
    # This is explicitly a process-delivery metric, not a scientific truth label.
    # The no-mechanism base is a designed control and is therefore not counted as
    # a delivery failure; all assigned mechanism arms must emit their contract.
    result = result or {}
    status = result.get("execution_status", "MISSING")
    required = required_events(row.get("arm_id", ""))
    observed = event_types(result)
    observed_failure = bool(status != "PASS" or (required and not required.issubset(observed)))
    if not required and row.get("arm_id") == "A_G3_BASE":
        observed_failure = status != "PASS"
    return {
        "run_id": row["run_id"],
        "audited": True,
        "target_failure_mode": row.get("target_failure_mode"),
        "target_failure_observed": observed_failure,
        "evidence_ref": f"{row['run_id']}/result.json#independent_process_contract",
        "audit_basis": "assigned mechanism event contract and execution status; not a scientific correctness judgment",
        "execution_status": status,
        "audit_status": (review or {}).get("status", "MISSING"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    plan = rows(args.plan)
    reviews: list[dict[str, Any]] = []
    q_rows: list[dict[str, Any]] = []
    process_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    audit_counts: Counter[str] = Counter()
    result_ids: set[str] = set()
    verifier_hash = sha256(Path(__file__).resolve())

    for row in plan:
        path = args.raw / row["run_id"] / "result.json"
        result = load(path) if path.exists() else None
        if result:
            result_ids.add(row["run_id"])
        review = independently_check_result(row, result)
        reviews.append(review)
        status_counts[review.get("execution_status", "MISSING")] += 1
        audit_counts[review["status"]] += 1
        q = make_q_audit(row, result, verifier_hash)
        if q:
            q_rows.append(q)
        process_rows.append(make_process_audit(row, result, review))

    unexpected = sorted(result_ids - {r["run_id"] for r in plan})
    summary = {
        "audit_version": "g8-independent-output-audit-v1",
        "plan": str(args.plan),
        "raw": str(args.raw),
        "plan_sha256": sha256(args.plan),
        "n_planned": len(plan),
        "n_result_files": len(result_ids),
        "execution_status_counts": dict(sorted(status_counts.items())),
        "audit_status_counts": dict(sorted(audit_counts.items())),
        "n_q_audit_rows": len(q_rows),
        "n_process_audit_rows": len(process_rows),
        "unexpected_result_ids": unexpected,
        "private_oracle_loaded": False,
        "scientific_truth_decision_made": False,
        "note": "Technical failures remain in the formal ITT denominator; process audit is not a truth label.",
    }
    dump_json(args.out / "g8_independent_audit.json", summary)
    dump_jsonl(args.out / "g8_output_review.jsonl", reviews)
    dump_jsonl(args.out / "g8_q_audit.jsonl", q_rows)
    dump_jsonl(args.out / "g8_process_audit.jsonl", process_rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if len(result_ids) == len(plan) and not unexpected else 2


if __name__ == "__main__":
    raise SystemExit(main())
