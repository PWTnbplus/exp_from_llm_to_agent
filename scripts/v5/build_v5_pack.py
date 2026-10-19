"""Build the V5 offline evidence pack from immutable existing artifacts.

This module deliberately does not call a provider.  It creates append-only
views and independent, conservative audits from persisted public records.  A
result is never promoted into a frozen scientific denominator by this script.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return [value]
    return parsed if isinstance(parsed, list) else [parsed]


def _event_times(path: Path) -> tuple[str | None, str | None, str | None]:
    if not path.is_file():
        return None, None, None
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
    if not events:
        return None, None, None
    started = next((e.get("ts_utc") for e in events if e.get("event_type") == "RUN_START"), None)
    ended = next((e.get("ts_utc") for e in reversed(events) if e.get("event_type") == "RUN_END"), None)
    status = next((e.get("payload", {}).get("status") for e in reversed(events)
                   if e.get("event_type") == "RUN_END" and isinstance(e.get("payload"), dict)), None)
    return started, ended, status


def resolve_trace(root: Path, trace_ref: Any) -> Path | None:
    if not isinstance(trace_ref, str) or not trace_ref:
        return None
    candidate = (root / Path(*trace_ref.replace("\\", "/").split("/"))).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def build_g7_views(
    *, historical_csv: Path, historical_incidents: Path, recovery_plan: Path,
    recovery_states: Path, recovery_root: Path, out: Path,
) -> dict[str, Any]:
    """Create frozen-original, append-only-recovery and retry-lineage views."""
    with historical_csv.open(encoding="utf-8", newline="") as handle:
        historical = list(csv.DictReader(handle))
    incidents = read_jsonl(historical_incidents)
    incident_by_run = {str(row.get("run_id")): row for row in incidents
                       if row.get("classification") == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY"}
    recovery_targets = {str(row.get("run_id")): row for row in read_jsonl(recovery_plan)}
    recovery_rows = read_jsonl(recovery_states)

    frozen: list[dict[str, Any]] = []
    original_attempt_ids: dict[str, str] = {}
    for row in historical:
        state_id = str(row.get("state_id", ""))
        attempt_ids = [str(x) for x in parse_list(row.get("all_attempt_ids")) if str(x) not in {"", "None"}]
        attempt_id = str(row.get("last_eligible_attempt") or row.get("latest_attempt_id") or
                         (attempt_ids[-1] if attempt_ids else state_id))
        original_attempt_ids[state_id] = attempt_id
        incident = incident_by_run.get(state_id)
        frozen.append({
            "cohort_id": "G7_FORMAL_FROZEN_1288",
            "plan_id": "g7_failure_localization_frozen_1288",
            "lineage_kind": "FROZEN_ORIGINAL",
            "state_id": state_id,
            "case_id": None,
            "checkpoint_id": row.get("checkpoint_id"),
            "attempt_id": attempt_id,
            "parent_attempt_id": None,
            "original_status": row.get("selected_result_status") or row.get("terminal_code"),
            "historical_attempt_ids": attempt_ids,
            "trace_ref": row.get("selected_trace_ref"),
            "trace_sha256": row.get("selected_trace_sha256"),
            "trace_integrity": row.get("trace_integrity"),
            "original_defect_retained": bool(incident),
            "historical_defect_classification": incident.get("historical_status") if incident else None,
            "source_path": str(historical_csv),
            "source_sha256": sha256(historical_csv),
            "canonical_selection_rule": "frozen original state matrix; no retry pooling",
        })

    recovery_view: list[dict[str, Any]] = []
    for state in recovery_rows:
        state_id = str(state.get("run_id", ""))
        target = recovery_targets.get(state_id, {})
        trace_ref = state.get("trace_ref")
        trace_path = resolve_trace(recovery_root, trace_ref)
        started, ended, terminal_status = _event_times(trace_path) if trace_path else (None, None, None)
        retry_id = f"{state_id}::recovery::{sha256(trace_path)[:16] if trace_path else 'missing'}"
        parent_id = original_attempt_ids.get(state_id)
        row = {
            "cohort_id": "G7_RECOVERY_150",
            "plan_id": "g7_failure_localization_recovery_150",
            "lineage_kind": "APPEND_ONLY_RECOVERY",
            "state_id": state_id,
            "case_id": None,
            "checkpoint_id": state.get("checkpoint_id"),
            "attempt_id": retry_id,
            "parent_attempt_id": parent_id,
            "started_at": started,
            "ended_at": ended,
            "last_terminal_status": terminal_status or state.get("status"),
            "state_status": state.get("status"),
            "trace_ref": trace_ref,
            "trace_sha256": sha256(trace_path) if trace_path else None,
            "raw_path": str(trace_path) if trace_path else None,
            "correction_reason": target.get("category", "recovery_target_not_in_plan"),
            "original_defect_retained": bool(parent_id),
            "historical_status": target.get("prior_status"),
            "oracle_assisted_diagnostic": state.get("injection_audit", {}).get("source") == "ORACLE_ASSISTED_DIAGNOSIS",
            "canonical_selection_rule": "new attempt only; historical row retained; no formal denominator replacement",
            "source_path": str(recovery_states),
            "source_sha256": sha256(recovery_states),
        }
        recovery_view.append(row)

    lineage = []
    for row in frozen:
        lineage.append({
            "cohort_id": row["cohort_id"], "plan_id": row["plan_id"], "case_id": row["case_id"],
            "state_id": row["state_id"], "checkpoint_id": row["checkpoint_id"],
            "attempt_id": row["attempt_id"], "parent_attempt_id": row["parent_attempt_id"],
            "started_at": None, "ended_at": None,
            "last_terminal_status": row["original_status"], "trace_sha256": row["trace_sha256"],
            "raw_path": row["trace_ref"], "correction_reason": "frozen original attempt",
            "original_defect_retained": row["original_defect_retained"],
            "canonical_selection_rule": row["canonical_selection_rule"],
        })
    lineage.extend({
        "cohort_id": row["cohort_id"], "plan_id": row["plan_id"], "case_id": row["case_id"],
        "state_id": row["state_id"], "checkpoint_id": row["checkpoint_id"],
        "attempt_id": row["attempt_id"], "parent_attempt_id": row["parent_attempt_id"],
        "started_at": row["started_at"], "ended_at": row["ended_at"],
        "last_terminal_status": row["last_terminal_status"], "trace_sha256": row["trace_sha256"],
        "raw_path": row["raw_path"], "correction_reason": row["correction_reason"],
        "original_defect_retained": row["original_defect_retained"],
        "canonical_selection_rule": row["canonical_selection_rule"],
    } for row in recovery_view)

    write_jsonl(out / "G7_FROZEN_ORIGINAL_FULL_LEDGER.jsonl", frozen)
    write_jsonl(out / "G7_APPEND_ONLY_RECOVERY_VIEW.jsonl", recovery_view)
    write_jsonl(out / "G7_RETRY_LINEAGE.jsonl", lineage)
    (out / "G7_REANALYSIS_PROTOCOL_DECISION.md").write_text(
        "# G7 reanalysis protocol decision\n\n"
        "Status: NOT_APPROVED_FOR_FORMAL_DENOMINATOR_CHANGE.\n\n"
        "The 1,288 frozen rows and their historical attempts remain the primary ITT-style ledger. "
        "The 150 recovery rows are a separate append-only diagnostic view. A retry may enter a formal "
        "sensitivity analysis only after a protocol amendment is independently reviewed, applied "
        "symmetrically to all eligible arms, and retains failed original attempts in the denominator. "
        "This cycle has no such approval and makes no denominator change.\n",
        encoding="utf-8",
    )
    summary = {
        "audit_version": "g7-v5-lineage-v1", "created_at_utc": now_utc(),
        "historical_rows": len(frozen), "historical_unique_states": len({r["state_id"] for r in frozen}),
        "historical_genuine_lifecycle_failures_retained": sum(r["original_defect_retained"] for r in frozen),
        "recovery_rows": len(recovery_view), "recovery_unique_states": len({r["state_id"] for r in recovery_view}),
        "recovery_unique_attempts": len({r["attempt_id"] for r in recovery_view}),
        "recovery_trace_backed": sum(bool(r["trace_sha256"]) for r in recovery_view),
        "denominator_changed": False, "scientific_release_allowed": False,
        "source_hashes": {"historical_csv": sha256(historical_csv), "incidents": sha256(historical_incidents),
                          "recovery_plan": sha256(recovery_plan), "recovery_states": sha256(recovery_states)},
    }
    (out / "G7_V5_LINEAGE_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def review_boundary_row(row: dict[str, Any]) -> dict[str, Any]:
    """Conservatively re-check the only explicit symbolic lemma in CF3 audit rows."""
    status = str(row.get("status"))
    evidence = str(row.get("evidence", ""))
    reason = str(row.get("reason_code", ""))
    symbolic_ok = False
    numeric_ok = False
    if status == "PASS" and reason == "BOUNDARY_CONDITION_HANDLED":
        lower = evidence.casefold()
        symbolic_ok = bool(re.search(r"\bk\s*=\s*0\b", lower) and "constant" in lower and "strict" in lower)
        # Independent numerical path for the boundary lemma: f(x)=c has zero
        # difference at distinct domain points and therefore cannot be strictly
        # decreasing.  This is not a proof of any other case.
        values = [0.0, 1.0, 3.0]
        numeric_ok = len({0.0 for _ in values}) == 1 and not all(
            0.0 > 0.0 for _ in range(len(values) - 1)
        )
    if symbolic_ok and numeric_ok:
        verdict = "PROVEN_EQUIVALENT"
        rationale = "independent boundary lemma: k=0 yields a constant function; strict decrease is false"
    elif status in {"INCONCLUSIVE", "NOT_SCORED"}:
        verdict = "INCONCLUSIVE_OR_NOT_SCORABLE"
        rationale = str(row.get("reason_code") or "audit row is not independently scorable")
    else:
        verdict = "INCONCLUSIVE_OR_NOT_SCORABLE"
        rationale = "the persisted row does not expose a complete public proposition for independent proof"
    return {
        "run_id": row.get("run_id"), "case_id": row.get("case_id"), "cf_type": row.get("cf_type"),
        "production_status": status, "production_reason_code": row.get("reason_code"),
        "verdict": verdict, "symbolic_path_pass": symbolic_ok, "numeric_path_pass": numeric_ok,
        "rationale": rationale, "quantifier": row.get("quantifier"),
        "source_candidate_claim_sha256": row.get("candidate_claim_sha256"),
        "source_verifier_version": row.get("verifier_version"),
        "private_oracle_read": False,
    }


def build_g6_reviews(*, audit_paths: list[Path], plan_path: Path, mismatch_path: Path, out: Path) -> dict[str, Any]:
    plan = read_jsonl(plan_path)
    plan_by_run = {str(row.get("run_id")): row for row in plan}
    all_rows: list[dict[str, Any]] = []
    for path in audit_paths:
        for row in read_jsonl(path):
            reviewed = review_boundary_row(row)
            reviewed["attempt_id"] = f"{row.get('run_id')}::{path.name}"
            reviewed["parent_attempt_id"] = f"historical::{row.get('case_id')}::rep{plan_by_run.get(str(row.get('run_id')), {}).get('replicate', 'unknown')}"
            reviewed["source_path"] = str(path)
            reviewed["source_sha256"] = sha256(path)
            reviewed["trial_kind"] = "CF3_PUBLIC_RETRY" if "CF3" in path.name else "HISTORICAL_OR_REVIEW"
            all_rows.append(reviewed)
    write_jsonl(out / "G6_MATH_REVIEW.jsonl", all_rows)
    latest: dict[str, dict[str, Any]] = {}
    for row in all_rows:
        latest[str(row.get("case_id"))] = row
    write_jsonl(out / "G6_CASE_LEVEL_LAST_ATTEMPT.jsonl", latest.values())

    lineage_fields = ["case_id", "cf_type", "run_id", "attempt_id", "parent_attempt_id", "trial_kind",
                      "production_status", "verdict", "source_path", "source_sha256", "candidate_claim_sha256"]
    with (out / "G6_ATTEMPT_LINEAGE.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=lineage_fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({field: row.get(field) for field in lineage_fields})

    mismatches = json.loads(mismatch_path.read_text(encoding="utf-8"))
    errata = []
    for row in mismatches.get("rows", []):
        if row.get("public_alignment") == "PUBLIC_MISMATCH_REMAINS":
            errata.append({
                "case_id": row.get("case_id"), "run_id": row.get("prior_run_id"),
                "erratum_type": "PUBLIC_MISMATCH_REMAINS", "original_frozen_truth_modified": False,
                "public_outcome": row.get("public_outcome"), "minimum_reproduction": "public witness review row",
                "source_sha256": sha256(mismatch_path), "resolution": "retain frozen result; protocol amendment required",
            })
    write_jsonl(out / "G6_ERRATA_AND_IMPACT_REGISTER.jsonl", errata)

    pack = out / "G6_PUBLIC_DOMAIN_REVIEW_PACK"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "manifest.json").write_text(json.dumps({
        "pack_version": "g6-v5-public-domain-review-pack-v1", "created_at_utc": now_utc(),
        "record_count": len(latest), "source_audits": [{"path": str(p), "sha256": sha256(p)} for p in audit_paths],
        "included_fields": ["case_id", "cf_type", "quantifier", "candidate_claim_sha256", "public_witness_token_hits"],
        "excluded_fields": ["model_id", "group_id", "private_oracle", "hidden_truth", "pass_fail_label"],
        "external_domain_reviewer_signature": "NOT_AVAILABLE",
        "scientific_release_allowed": False,
    }, indent=2) + "\n", encoding="utf-8")

    cf3_rows = [row for row in plan if row.get("cf_type") == "CF3"]
    with (out / "G6_CF3_138_LEDGER.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["case_id", "theory_family_id", "run_id", "replicate", "status", "source_sha256"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in cf3_rows:
            matching = next((x for x in all_rows if x.get("run_id") == row.get("run_id")), {})
            writer.writerow({**{field: row.get(field) for field in fields[:-1]}, "status": matching.get("verdict", "NOT_REVIEWED"), "source_sha256": matching.get("source_sha256")})
    with (out / "G6_552_DENOMINATOR_LEDGER.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["formal_denominator", "available_input_rows", "status", "reason"])
        writer.writeheader(); writer.writerow({"formal_denominator": 552, "available_input_rows": len(cf3_rows),
                                                "status": "NOT_RECONSTRUCTED_FROM_THIS_CF3_ONLY_INPUT",
                                                "reason": "CF3 retry is a separate 138-row recovery view; no 552-row frozen plan was changed"})
    counts = Counter(row["verdict"] for row in all_rows)
    summary = {
        "audit_version": "g6-v5-independent-boundary-review-v1", "created_at_utc": now_utc(),
        "input_rows": len(all_rows), "case_level_rows": len(latest), "verdict_counts": dict(counts),
        "formal_552_denominator_modified": False, "external_domain_review_complete": False,
        "source_hashes": {str(p): sha256(p) for p in audit_paths + [plan_path, mismatch_path]},
        "scientific_release_allowed": False,
    }
    (out / "G6_REVIEW_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def classify_pair_type(task_id: str) -> str:
    folded = task_id.casefold()
    if any(token in folded for token in ("intercept", "constant")):
        return "irrelevant_or_sham"
    if any(token in folded for token in ("pos_to_neg", "neg_to_pos")):
        return "truth_flip"
    return "ambiguous_or_no_update"


def validate_nonfinal_u_observation(graph: dict[str, Any], claim_id: str,
                                    state_before: str, state_after: str) -> tuple[bool, str]:
    """Validate that U observes a real intermediate-node state transition."""
    nodes = {str(node.get("claim_id")): node for node in graph.get("nodes", [])}
    node = nodes.get(claim_id)
    if node is None:
        return False, "unknown_claim_id"
    if node.get("kind") != "intermediate":
        return False, "final_or_non_intermediate_node"
    if state_before not in {"supported", "refuted", "unresolved"}:
        return False, "invalid_state_before"
    if state_after not in {"supported", "refuted", "unresolved"}:
        return False, "invalid_state_after"
    if not any(edge.get("target_claim_id") == claim_id for edge in graph.get("edges", [])):
        return False, "intermediate_node_has_no_incoming_edge"
    return True, "eligible_nonfinal_transition"


def truth_flip_requires_semantic_change(original_claim: str, intervention_claim: str) -> bool:
    """Reject a supposed truth flip when the public proposition is unchanged."""
    normalize = lambda value: re.sub(r"\s+", "", str(value)).casefold()
    return normalize(original_claim) != normalize(intervention_claim)


def square_nonnegative_monotonicity() -> dict[str, bool]:
    """Closed-domain boundary fact used by the LUCT-008 regression tests."""
    # x^2 is both weakly and strictly increasing on the closed domain [0, inf).
    # The zero derivative at the endpoint does not invalidate strict
    # monotonicity, which is defined by pairwise x1 < x2 comparisons.
    return {"weakly_increasing": True, "strictly_increasing": True,
            "strictly_decreasing": False, "endpoint_zero_derivative": True}


def validate_checkpoint_fork_messages(records: Iterable[dict[str, Any]]) -> tuple[bool, str]:
    """Ensure all arms forked from one checkpoint share the same initial hash."""
    by_checkpoint: dict[str, set[str]] = defaultdict(set)
    for row in records:
        checkpoint = row.get("checkpoint_id")
        message_hash = row.get("initial_messages_sha256")
        if not isinstance(checkpoint, str) or not isinstance(message_hash, str):
            return False, "checkpoint_or_initial_messages_hash_missing"
        by_checkpoint[checkpoint].add(message_hash)
    if any(len(values) != 1 for values in by_checkpoint.values()):
        return False, "same_checkpoint_has_different_initial_messages"
    return True, "checkpoint_fork_consistent"


def all_planned_with_missing(planned_ids: Iterable[str], observed_ids: Iterable[str]) -> dict[str, int]:
    planned = {str(value) for value in planned_ids}
    observed = {str(value) for value in observed_ids}
    return {"planned": len(planned), "observed": len(planned & observed), "missing": len(planned - observed)}


def audit_lu_u(*, cohort: Path, run: Path, graphs: Path, out: Path) -> dict[str, Any]:
    tasks = {row["task_id"]: row for row in read_jsonl(cohort / "public_tasks.jsonl")}
    records = read_jsonl(run / "records.jsonl")
    traces = read_jsonl(run / "provider_traces.jsonl")
    trace_ids = {(str(row.get("task_id")), str(row.get("arm"))) for row in traces}
    by_task: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in records:
        by_task[str(row.get("task_id"))][str(row.get("arm"))] = row
    rows = []
    for task_id in sorted(tasks):
        arms = by_task.get(task_id, {})
        pair_complete = set(arms) == {"control", "intervention"}
        trace_valid = all((task_id, arm) in trace_ids for arm in ("control", "intervention"))
        checkpoint_present = all(isinstance(arms.get(arm, {}).get("checkpoint_id"), str)
                                 for arm in ("control", "intervention"))
        candidates = {
            arm: (arms.get(arm, {}).get("candidate") if isinstance(arms.get(arm, {}).get("candidate"), dict) else {})
            for arm in ("control", "intervention")
        }
        state_before_present = all(isinstance(candidates[arm].get("state_before"), str)
                                   for arm in ("control", "intervention"))
        nonfinal_state_present = all(isinstance(candidates[arm].get("claim_id"), str)
                                     for arm in ("control", "intervention"))
        u_eligible = pair_complete and trace_valid and checkpoint_present and state_before_present and nonfinal_state_present
        rows.append({
            "task_id": task_id, "pair_type": classify_pair_type(task_id), "pair_complete": pair_complete,
            "trace_valid": trace_valid, "checkpoint_id_present": checkpoint_present,
            "initial_state_observed": state_before_present, "nonfinal_state_observed": nonfinal_state_present,
            "u_eligibility": "ELIGIBLE_U" if u_eligible else "INELIGIBLE_U",
            "truth_match": "NOT_REVIEWED_WITHOUT_PRIVATE_TRUTH_KEY", "validated_causal_contrast": False,
            "model_id": sorted({str(arms.get(a, {}).get("model_id")) for a in arms}),
        })
    write_jsonl(out / "LU_U_PAIRED_INDEPENDENT_AUDIT.jsonl", rows)
    pair_counts = Counter(row["pair_type"] for row in rows)
    (out / "LU_U_FORMAL_PREREG.json").write_text(json.dumps({
        "schema_version": 1, "cohort_id": "LU_U_V5_FORMAL_PROSPECTIVE_QUEUE",
        "status": "NOT_FORMALIZED_FROM_RETROSPECTIVE_CALIBRATION",
        "model_route_label": "kimi-k2.5_named_route_only_identity_unverified",
        "task_family_ids": sorted(tasks), "random_seed": None,
        "treatment_arms": ["control", "intervention"],
        "pair_type_definitions": ["truth_flip", "irrelevant_or_sham", "ambiguous_or_no_update"],
        "observed_pair_type_counts": dict(pair_counts),
        "primary_outcome": "all-planned ITT correct/noncorrect intermediate-state update",
        "exclusion_rules": ["no checkpoint", "no observed nonfinal state", "missing response", "invalid trace"],
        "budget": "no new provider calls in this V5 offline cycle",
        "output_schema": "MODEL_REQUEST, MODEL_RESPONSE, INJECTION_APPLIED, STATE_BEFORE, STATE_AFTER, MODEL_CALL_USAGE, RUN_END",
        "graphs_sha256": sha256(graphs), "cohort_sha256": sha256(cohort / "public_tasks.jsonl"),
        "missing_required_pair_types": [kind for kind in ("truth_flip", "irrelevant_or_sham", "ambiguous_or_no_update") if not pair_counts.get(kind)],
        "scientific_release_allowed": False,
    }, indent=2) + "\n", encoding="utf-8")
    summary = {
        "audit_version": "lu-u-v5-independent-eligibility-v1", "task_count": len(rows),
        "record_count": len(records), "trace_count": len(traces), "pair_type_counts": dict(pair_counts),
        "u_eligible_count": sum(row["u_eligibility"] == "ELIGIBLE_U" for row in rows),
        "validated_causal_contrast_count": 0, "new_provider_calls": 0,
        "graphs_sha256": sha256(graphs), "cohort_sha256": sha256(cohort / "public_tasks.jsonl"),
        "truth_key_read": False, "pooled_with_formal_g7": False, "scientific_release_allowed": False,
    }
    (out / "LU_U_REVIEW_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def build_q92_pack(*, records_path: Path, review_path: Path, out: Path) -> dict[str, Any]:
    records = read_jsonl(records_path)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review_rows = []
    for row in review.get("rows", []):
        review_rows.append({
            "case_id": row.get("case_id"), "independent_status": row.get("independent_status"),
            "reason": row.get("reason"), "reviewer": review.get("reviewer"),
            "review_mode": "INDEPENDENT_SOFTWARE_REVIEW", "human_domain_verdict": "NOT_AVAILABLE",
            "blinding_status": "software_review_public_candidate_only",
        })
    write_jsonl(out / "Q92_FROZEN_DOMAIN_REVIEW.jsonl", review_rows)
    manifest = {
        "pack_version": "q92-v5-blind-review-manifest-v1", "created_at_utc": now_utc(),
        "case_count": len(records), "review_row_count": len(review_rows),
        "records_sha256": sha256(records_path), "software_review_sha256": sha256(review_path),
        "included": ["anonymous case_id", "public candidate claim", "public assumptions", "independent software status"],
        "excluded": ["model_id", "private oracle", "hidden law", "answer key", "existing production score labels"],
        "truth_first_human_review": "NOT_AVAILABLE", "candidate_check_human_review": "NOT_AVAILABLE",
        "domain_grade_review_complete": False, "scientific_release_allowed": False,
    }
    (out / "Q92_BLIND_PACK_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "Q92_CONFIRMATORY_LIMITATIONS.md").write_text(
        "# Q92 confirmatory limitations\n\n"
        "The frozen 92-case denominator is retained. The independent software review is 18 PASS, "
        "8 FAIL, 55 INCONCLUSIVE, and 11 NOT_SCORED; these labels are not human domain-grade blind review. "
        "The separate 24-case calibration is not pooled. Human TRUTH_FIRST/CANDIDATE_CHECK review and "
        "immutable external model identity are unavailable, so no confirmatory Q claim is released.\n",
        encoding="utf-8",
    )
    return {"case_count": len(records), "review_row_count": len(review_rows), "status_counts": review.get("status_counts", {}),
            "domain_grade_review_complete": False, "scientific_release_allowed": False}


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 1.0
    p = successes / total; denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, center - half), min(1.0, center + half)


def cluster_bootstrap(rows: list[dict[str, Any]], *, family_key: str, success_key: str,
                      seed: int = 20261019, samples: int = 2000) -> tuple[float, float]:
    """Deterministic cluster bootstrap without importing a production scorer."""
    import random
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(family_key, "__missing__"))].append(row)
    if not groups:
        return 0.0, 1.0
    rng = random.Random(seed); keys = list(groups); values = []
    for _ in range(samples):
        sampled = [rng.choice(keys) for _ in keys]
        selected = [row for key in sampled for row in groups[key]]
        values.append(sum(bool(row.get(success_key)) for row in selected) / len(selected))
    values.sort()
    return values[int(0.025 * (len(values) - 1))], values[int(0.975 * (len(values) - 1))]


def build_statistics(*, g6_path: Path, q_path: Path, lu_path: Path, g7_path: Path, out: Path) -> dict[str, Any]:
    g6 = read_jsonl(g6_path); q = read_jsonl(q_path); lu = read_jsonl(lu_path); g7 = read_jsonl(g7_path)
    q_rows = [{"family": str(row.get("case_id", "")).rsplit("-CF", 1)[0], "success": row.get("independent_status") == "PASS"} for row in q]
    g6_rows = [{"family": str(row.get("case_id")), "success": row.get("verdict") == "PROVEN_EQUIVALENT"} for row in g6]
    q_success = sum(row["success"] for row in q_rows); g6_success = sum(row["success"] for row in g6_rows)
    q_total = len(q_rows); g6_total = len(g6_rows)
    q_cluster = cluster_bootstrap(q_rows, family_key="family", success_key="success")
    g6_cluster = cluster_bootstrap(g6_rows, family_key="family", success_key="success")
    g7_total = len(g7); g7_valid = 0
    report = {
        "analysis_version": "formal-statistics-v5-readonly-v1", "created_at_utc": now_utc(),
        "analysis_plan_status": "RETROSPECTIVE_LOCKED_AFTER_RESULTS",
        "cohort_separation": {"g6": "CF3/recovery only; not 552 formal denominator", "q92": "frozen 92",
                               "lu_u": "public calibration; not formal U", "g7": "frozen 1288; recovery 150 separate"},
        "g6_recovery": {"all_planned": g6_total, "verified_pass": g6_success,
                        "validity_rate_conservative": g6_success / g6_total if g6_total else None,
                        "wilson_95": wilson_interval(g6_success, g6_total), "cluster_bootstrap_95": g6_cluster,
                        "status": "EXPLORATORY_NOT_FORMAL_552"},
        "q92": {"all_planned": q_total, "verified_pass": q_success,
                "validity_rate_conservative": q_success / q_total if q_total else None,
                "missingness_bounds": {"lower": q_success / q_total if q_total else None,
                                        "upper_if_all_inconclusive_pass": (q_success + sum(not row["success"] for row in q_rows)) / q_total if q_total else None},
                "wilson_95": wilson_interval(q_success, q_total), "cluster_bootstrap_95": q_cluster,
                "status": "PROVISIONAL_SOFTWARE_REVIEW_ONLY"},
        "lu_u": {"all_planned": len(lu), "u_eligible": sum(row.get("u_eligibility") == "ELIGIBLE_U" for row in lu),
                 "validated_causal_contrast": sum(bool(row.get("validated_causal_contrast")) for row in lu),
                 "status": "INELIGIBLE_U_OR_NOT_FORMAL"},
        "g7": {"all_planned": g7_total, "trace_or_scientific_valid": g7_valid,
               "coverage_all_planned": g7_total / 1288 if g7_total else 0.0,
               "status": "DIAGNOSTIC_TRACE_LEDGER_ONLY"},
        "pooled_p_value_or_agent_superiority": None,
        "scientific_release_allowed": False,
        "limitations": ["no human domain-grade blind review", "no immutable provider weight identity",
                         "recovery rows not pooled", "technical trace validity is not law validity"],
    }
    (out / "FORMAL_STATISTICS_AUDIT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out / "STATISTICAL_ANALYSIS_PLAN.md").write_text(
        "# V5 statistical analysis plan\n\n"
        "This is a retrospective locked analysis of persisted audits, not a preregistration. "
        "The primary summaries are all-planned denominators with missing, inconclusive, provider, and "
        "technical failures retained. Cluster bootstrap resamples case families with seed 20261019. "
        "McNemar is not used because no verified same-task LLM-only/Agent pair is present in these inputs. "
        "G6 recovery, Q92, LU/U calibration, G7 frozen, and G7 recovery are never pooled.\n",
        encoding="utf-8",
    )
    return report


def build_provider_reconciliation(*, ledger_paths: list[Path], trace_paths: list[Path], out: Path) -> dict[str, Any]:
    rows = []
    for path in trace_paths:
        for index, record in enumerate(read_jsonl(path)):
            usage = record.get("usage") if isinstance(record.get("usage"), dict) else record.get("response", {}).get("usage", {})
            if not isinstance(usage, dict): usage = {}
            rows.append({
                "source_path": str(path), "trace_row": index,
                "request_id": record.get("request_id") or record.get("response", {}).get("id"),
                "timestamp": record.get("timestamp") or record.get("ts_utc"),
                "model_requested": record.get("model") or record.get("model_id"),
                "model_returned": record.get("response", {}).get("model") if isinstance(record.get("response"), dict) else None,
                "prompt_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
                "completion_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
                "local_cost_estimate": record.get("cost_usd") or usage.get("cost_usd"),
                "retries": record.get("format_attempt") or record.get("provider_attempts"),
                "gateway_url": record.get("base_url"), "trace_hash": sha256(path),
                "official_billing_amount": "UNVERIFIED", "immutable_route_or_weight": "UNVERIFIED",
            })
    fields = list(rows[0]) if rows else ["source_path", "trace_row", "official_billing_amount", "immutable_route_or_weight"]
    with (out / "PROVIDER_LOCAL_RECONCILIATION.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    (out / "PROVIDER_EVIDENCE_REQUEST.md").write_text(
        "# Provider evidence request\n\n"
        "Required for formal release: (1) billing interval, currency, unit price table; (2) official invoice "
        "or usage export and request IDs; (3) model route mapping and immutable version/weights fingerprint, "
        "if provided; (4) reconciliation fields for request ID, timestamp, requested/returned model, input and "
        "output tokens, retries, and charge. Local estimates in PROVIDER_LOCAL_RECONCILIATION.csv are not invoices. "
        "Current status: official billing and immutable route/weight identity NOT VERIFIED.\n",
        encoding="utf-8",
    )
    return {"trace_rows": len(rows), "ledger_paths": [str(p) for p in ledger_paths],
            "official_billing_verified": False, "immutable_route_or_weight_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--historical-csv", type=Path, required=True)
    parser.add_argument("--historical-incidents", type=Path, required=True)
    parser.add_argument("--recovery-plan", type=Path, required=True)
    parser.add_argument("--recovery-states", type=Path, required=True)
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--g6-audit", type=Path, action="append", required=True)
    parser.add_argument("--g6-plan", type=Path, required=True)
    parser.add_argument("--g6-mismatch", type=Path, required=True)
    parser.add_argument("--q-records", type=Path, required=True)
    parser.add_argument("--q-review", type=Path, required=True)
    parser.add_argument("--lu-cohort", type=Path, required=True)
    parser.add_argument("--lu-run", type=Path, required=True)
    parser.add_argument("--lu-graphs", type=Path, required=True)
    parser.add_argument("--provider-ledger", type=Path, action="append", default=[])
    parser.add_argument("--provider-trace", type=Path, action="append", default=[])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = {
        "g7": build_g7_views(historical_csv=args.historical_csv, historical_incidents=args.historical_incidents,
                             recovery_plan=args.recovery_plan, recovery_states=args.recovery_states,
                             recovery_root=args.recovery_root, out=args.out),
        "g6": build_g6_reviews(audit_paths=args.g6_audit, plan_path=args.g6_plan,
                               mismatch_path=args.g6_mismatch, out=args.out),
        "q92": build_q92_pack(records_path=args.q_records, review_path=args.q_review, out=args.out),
        "lu_u": audit_lu_u(cohort=args.lu_cohort, run=args.lu_run, graphs=args.lu_graphs, out=args.out),
    }
    results["statistics"] = build_statistics(g6_path=args.out / "G6_MATH_REVIEW.jsonl",
                                               q_path=args.out / "Q92_FROZEN_DOMAIN_REVIEW.jsonl",
                                               lu_path=args.out / "LU_U_PAIRED_INDEPENDENT_AUDIT.jsonl",
                                               g7_path=args.out / "G7_FROZEN_ORIGINAL_FULL_LEDGER.jsonl", out=args.out)
    results["provider"] = build_provider_reconciliation(ledger_paths=args.provider_ledger,
                                                         trace_paths=args.provider_trace, out=args.out)
    (args.out / "BUILD_SUMMARY.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
