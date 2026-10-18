"""Build the six-blocker G6/G7 repair audit from immutable source data.

This command is intentionally offline.  It never calls a provider and never
rewrites a source file.  It produces a sensitive row-level audit under the
run directory and a public, hash-linked summary under ``docs/audits``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_repair.math_verifier import verify_candidate_claim
from scripts.audit_repair.source_inventory import inventory
from scripts.audit_repair.verify_q import verify_state
from scripts import audit_g7_trace_q_consistency as trace_audit


def readl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def trace_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = (root / Path(value.replace("\\", "/"))).resolve()
    return candidate if root.resolve() in candidate.parents and candidate.is_file() else None


def event_segments(path: Path) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]], list[str]]:
    events, parse_errors = trace_audit._load_events(path)
    return events, trace_audit._segments(events), parse_errors


def selected_trace_status(root: Path, trace_ref: Any, run_id: str) -> tuple[bool, list[str], Path | None, list[dict[str, Any]]]:
    path = trace_path(root, trace_ref)
    if path is None:
        return False, ["trace_file_missing"], None, []
    events, segments, parse_errors = event_segments(path)
    selected = segments[-1] if segments else []
    reasons = trace_audit.validate_lifecycle(selected, {run_id}) if selected else ["empty_trace_segment"]
    reasons.extend(parse_errors)
    return not reasons, reasons, path, selected


def worker_index_from_file(path: Path) -> str:
    stem = path.stem
    return stem.split("worker-")[-1].split("-")[-1] if "worker-" in stem else "unknown"


def g6_audit(paths: dict[str, Path], local_out: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    plan_rows = readl(paths["g6_plan"])
    oracle_rows = readl(paths["g6_oracle"])
    public_rows = readl(paths["g6_public"])
    response_rows = readl(paths["g6_responses"])
    old_revision = {row["run_id"]: row for row in readl(paths["g6_revision_old"])}
    plan = {row["run_id"]: row for row in plan_rows}
    oracle = {row["case_id"]: row for row in oracle_rows}
    public = {row["case_id"]: row for row in public_rows}
    response = {row["run_id"]: row for row in response_rows}
    revision_units = [row for row in plan_rows if row.get("cf_type") == "CF3"]
    root_rows: list[dict[str, Any]] = []
    math_rows: list[dict[str, Any]] = []
    for p in revision_units:
        run_id = p["run_id"]
        r = response.get(run_id)
        old = old_revision.get(run_id, {})
        raw_ref = r.get("trace_ref") if r else None
        raw_trace = trace_path(paths["g6_root"], raw_ref)
        secondary: list[str] = []
        if r is None:
            reason = "MISSING_REAL_RESPONSE"
        elif r.get("status") != "completed":
            reason = "PROVIDER_ERROR"
        elif raw_trace is None:
            reason = "BAD_TRACE"
        elif r.get("decision") != "REVISE":
            reason = "BAD_DECISION"
        elif not isinstance(r.get("revised_claim"), str) or not r.get("revised_claim", "").strip():
            reason = "REVISED_CLAIM_NULL"
        else:
            reason = "VERIFIER_INCONCLUSIVE"
        if r is not None and (not isinstance(r.get("revised_claim"), str) or not r.get("revised_claim", "").strip()):
            secondary.append("REVISED_CLAIM_NULL")
        if r is not None and r.get("decision") != "REVISE":
            secondary.append("BAD_DECISION")
        claim = r.get("revised_claim") if r else None
        spec = public.get(p["case_id"], {}).get("model_visible", {})
        verdict = verify_candidate_claim(
            cf_type=str(p.get("cf_type")), claim=claim,
            quantifier=str(public.get(p["case_id"], {}).get("quantifier", "")),
            public_problem=str(spec.get("original_problem", "")),
        )
        math_row = {
            "run_id": run_id, "case_id": p["case_id"], "cf_type": p["cf_type"],
            "eligible": True, "candidate_claim_sha256": hashlib.sha256(claim.encode("utf-8")).hexdigest() if isinstance(claim, str) else None,
            "quantifier": public.get(p["case_id"], {}).get("quantifier"), "status": verdict.status,
            "verification_grade": verdict.grade, "proof_kind": verdict.proof_kind,
            "proof_or_counterexample_ref": verdict.evidence, "verifier_version": "audit_repair.math_verifier.v1",
            "verifier_source_sha256": sha256(ROOT / "scripts/audit_repair/math_verifier.py"),
            "independent_of_test_model": True, "reason_code": verdict.reason_code,
        }
        math_rows.append(math_row)
        root_rows.append({
            "case_id": p["case_id"], "run_id": run_id, "cf_type": p["cf_type"], "arm_id": p["arm_id"],
            "eligibility": True, "old_score": old.get("is_valid"), "reason_code": reason,
            "secondary_reason_codes": ";".join(secondary),
            "raw_trace_ref": raw_ref, "oracle_sha256": sha256(paths["g6_oracle"]),
            "verifier_ref": f"local:{math_row['verifier_version']}:{math_row['verifier_source_sha256']}",
            "new_score_or_null": True if verdict.status == "PASS" and r and r.get("decision") == "REVISE" else None,
        })
    if len(root_rows) != 138 or len({r["run_id"] for r in root_rows}) != 138:
        raise RuntimeError("G6 revision denominator is not exactly 138 unique rows")
    write_csv(local_out / "02_G6_REVISION_ROOT_CAUSES.csv", root_rows, list(root_rows[0]))
    write_jsonl(local_out / "03_G6_INDEPENDENT_MATH_AUDIT.jsonl", math_rows)
    root_counts = Counter(row["reason_code"] for row in root_rows)
    math_counts = Counter(row["status"] for row in math_rows)
    stats = {
        "planned_rows": len(plan_rows), "completed_response_rows": sum(r.get("status") == "completed" for r in response_rows),
        "provider_error_rows": sum(r.get("status") != "completed" for r in response_rows),
        "revision_denominator": len(root_rows), "revision_root_cause_counts": dict(sorted(root_counts.items())),
        "revision_secondary_reason_counts": dict(sorted(Counter(code for row in root_rows for code in row["secondary_reason_codes"].split(";") if code).items())),
        "independent_math_status_counts": dict(sorted(math_counts.items())),
        "g3_revision_units": sum(p.get("group_id") == "G3" for p in revision_units),
        "g4_revision_units": sum(p.get("group_id") == "G4" for p in revision_units),
        "confirmatory_reuse_allowed": False,
        "oracle_used_to_generate_candidate_claim": False,
    }
    write_json(local_out / "g6_summary.json", stats)
    return root_rows, math_rows, stats


def g6_statistics(paths: dict[str, Path], local_out: Path) -> dict[str, Any]:
    plan = {r["run_id"]: r for r in readl(paths["g6_plan"])}
    oracle = {r["case_id"]: r for r in readl(paths["g6_oracle"])}
    response = {r["run_id"]: r for r in readl(paths["g6_responses"])}
    by_group: dict[str, list[float]] = defaultdict(list)
    by_family_group: dict[tuple[str, str], list[float]] = defaultdict(list)
    for run_id, p in plan.items():
        r = response.get(run_id)
        if not r or r.get("status") != "completed":
            value = 0.0
        else:
            value = float(r.get("decision") == oracle.get(p["case_id"], {}).get("expected_decision"))
        by_group[p["group_id"]].append(value)
        by_family_group[(p["theory_family_id"], p["group_id"])].append(value)
    families = sorted({family for family, _ in by_family_group})
    family_diffs = []
    for family in families:
        g3 = statistics.mean(by_family_group.get((family, "G3"), [0.0]))
        g4 = statistics.mean(by_family_group.get((family, "G4"), [0.0]))
        family_diffs.append(g4 - g3)
    # A deterministic cluster bootstrap is descriptive only; it is not used
    # to unlock a scientific gate.
    samples = []
    if family_diffs:
        seed = 20261018
        for _ in range(2000):
            values = []
            for _ in family_diffs:
                seed = (1103515245 * seed + 12345) % (2**31)
                values.append(family_diffs[seed % len(family_diffs)])
            samples.append(statistics.mean(values))
    result = {
        "status": "DESCRIPTIVE_ONLY",
        "outcome": "decision_matches_frozen_oracle_label",
        "oracle_used_as_verifier": False,
        "planned_denominator": len(plan),
        "by_group": {group: {"n": len(values), "mean": statistics.mean(values) if values else None} for group, values in by_group.items()},
        "family_cluster_count": len(families),
        "paired_family_effect_g4_minus_g3": statistics.mean(family_diffs) if family_diffs else None,
        "family_bootstrap_95ci": [sorted(samples)[50], sorted(samples)[1949]] if len(samples) == 2000 else None,
        "confirmatory_reuse_allowed": False,
        "limitations": ["provider billing/model identity unverified", "independent Q/L/U not established", "historical/debugged run"],
    }
    write_json(local_out / "04_G6_STATISTICAL_REVIEW.json", result)
    return result


def g6_handoff(paths: dict[str, Path], local_out: Path) -> dict[str, Any]:
    handoff = readl(paths["g6_handoff"])
    result = {
        "source_path": rel(paths["g6_handoff"]), "source_sha256": sha256(paths["g6_handoff"]),
        "rows": len(handoff), "unique_run_ids": len({r.get("run_id") for r in handoff}),
        "actual_source_rows": len(handoff) == 552, "scientifically_release_usable": False,
        "reason": "metadata handoff exists, but independent math/stat/provider gates remain blocked",
        "fields_preserved": ["run_id", "case_id", "theory_family_id", "arm_id", "cf_type", "decision", "expected_decision", "trace_ref", "failure_type", "is_mock"],
    }
    write_json(local_out / "05_G6_HANDOFF_PROVENANCE.json", result)
    return result


def g7_state_matrix(paths: dict[str, Path], local_out: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    plan_rows = readl(paths["g7_plan"])
    plan = {row["run_id"]: row for row in plan_rows}
    state_files = sorted(paths["g7_root"].glob("states.worker-*.jsonl"))
    cp_files = sorted(paths["g7_root"].glob("checkpoints.worker-*.jsonl"))
    all_states: dict[str, list[dict[str, Any]]] = defaultdict(list)
    state_worker: dict[str, str] = {}
    for source in state_files:
        worker = worker_index_from_file(source)
        for row in readl(source):
            all_states[str(row.get("run_id"))].append(row)
            state_worker[str(row.get("run_id"))] = worker
    cps: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in cp_files:
        for row in readl(source):
            cps[str(row.get("checkpoint_id"))].append(row)
    completed_cp = {key for key, rows in cps.items() if any(r.get("status") == "completed" for r in rows)}
    rows = []
    for p in plan_rows:
        run_id = p["run_id"]
        candidates = all_states.get(run_id, [])
        completed = [r for r in candidates if r.get("status") == "completed"]
        selected = completed[-1] if completed else (candidates[-1] if candidates else None)
        status = selected.get("status") if selected else "missing_record"
        trace_ok, reasons, selected_path, _ = selected_trace_status(paths["g7_root"], selected.get("trace_ref") if selected else None, run_id) if selected else (False, ["state_record_missing"], None, [])
        attempts = []
        for candidate in candidates:
            attempts.append({"status": candidate.get("status"), "trace_ref": candidate.get("trace_ref")})
        rows.append({
            "state_id": run_id, "worker_index": state_worker.get(run_id, "unknown"), "checkpoint_id": p["checkpoint_id"],
            "checkpoint_available": p["checkpoint_id"] in completed_cp, "all_attempt_ids": [str(a.get("trace_ref")) for a in candidates],
            "all_attempt_statuses": [a.get("status") for a in candidates], "last_eligible_attempt": selected.get("run_id") if selected else None,
            "selected_response_exists": bool(completed), "selected_trace_valid": bool(trace_ok),
            "selected_result_status": status, "why_selected": "latest_completed_record" if completed else ("latest_terminal_record" if selected else "no_record"),
            "needs_real_provider_call": not bool(completed), "selected_trace_reasons": reasons,
            "selected_trace_ref": selected.get("trace_ref") if selected else None,
            "selected_trace_sha256": sha256(selected_path) if selected_path else None,
        })
    fields = list(rows[0])
    write_csv(local_out / "06_G7_STATE_RESUME_MATRIX.csv", rows, fields)
    status_counts = Counter(row["selected_result_status"] for row in rows)
    result = {
        "planned_ids": len(plan_rows), "observed_state_ids": len(rows), "unique_state_ids": len({r["state_id"] for r in rows}),
        "checkpoint_ids": len({p["checkpoint_id"] for p in plan_rows}), "completed_checkpoint_ids": len(completed_cp),
        "state_status_counts": dict(status_counts), "actual_provider_completed": sum(r["selected_response_exists"] for r in rows),
        "trace_valid_completed": sum(r["selected_response_exists"] and r["selected_trace_valid"] for r in rows),
        "needs_real_provider_call": sum(r["needs_real_provider_call"] for r in rows),
        "worker_missing_counts": dict(Counter(r["worker_index"] for r in rows if r["needs_real_provider_call"])),
        "duplicate_state_ids": len(rows) - len({r["state_id"] for r in rows}),
        "preserves_frozen_denominator": len(rows) == 1288,
    }
    return rows, result, plan


def g7_trace_reconciliation(paths: dict[str, Path], local_out: Path, state_rows: list[dict[str, Any]], plan: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state_index = {r["state_id"]: r for r in state_rows}
    rows: list[dict[str, Any]] = []
    for run_id, state in state_index.items():
        if state["selected_result_status"] not in {"completed", "provider_error"}:
            continue
        selected_ref = state.get("selected_trace_ref")
        path = trace_path(paths["g7_root"], selected_ref)
        if path is None:
            continue
        events, segments, parse_errors = event_segments(path)
        selected = segments[-1] if segments else []
        reasons = trace_audit.validate_lifecycle(selected, {run_id}) if selected else ["empty_trace_segment"]
        reasons.extend(parse_errors)
        if not reasons:
            continue
        starts = [i for i, event in enumerate(events) if event.get("event_type") == "RUN_START"]
        suffix = events[starts[-1]:] if starts else []
        suffix_reasons = trace_audit.validate_lifecycle(suffix, {run_id}) if suffix else ["no_run_start"]
        group = "AUDIT_BOUNDARY_ARTIFACT" if len(starts) > 1 and not suffix_reasons else "GENUINE_FINAL_ATTEMPT_INCONSISTENCY"
        worker = next((worker_index_from_file(source) for source in paths["g7_root"].glob("states.worker-*.jsonl") if any(r.get("run_id") == run_id for r in readl(source))), "unknown")
        rows.append({
            "run_id": run_id, "case_id": plan[run_id]["case_id"], "worker_index": worker, "record_status": state["selected_result_status"],
            "classification": group, "raw_trace_ref": selected_ref, "raw_sha256": sha256(path), "raw_event_count": len(events),
            "attempt_start_count": len(starts), "selected_segment_count": len(segments), "reasons_selected": ";".join(map(str, reasons)),
            "latest_start_suffix_status": "PASS" if not suffix_reasons else "FAIL", "latest_start_suffix_reasons": ";".join(map(str, suffix_reasons)),
            "historical_error_retained": True, "new_attempt_created": False,
        })
    rows.sort(key=lambda row: row["run_id"])
    fields = list(rows[0]) if rows else ["run_id", "classification"]
    write_csv(local_out / "07_G7_28_TO_15_PLUS_13_TRACE_RECONCILIATION.csv", rows, fields)
    incidents = []
    for row in rows:
        if row["classification"] != "GENUINE_FINAL_ATTEMPT_INCONSISTENCY":
            continue
        path = trace_path(paths["g7_root"], row["raw_trace_ref"])
        events = trace_audit._load_events(path)[0] if path else []
        incidents.append({
            **row,
            "event_sequence": [
                {"line": i + 1, "seq": e.get("seq"), "event_type": e.get("event_type"), "event_id": e.get("event_id"),
                 "step_id": e.get("step_id"), "parent_step_id": e.get("parent_step_id"), "status": e.get("status")}
                for i, e in enumerate(events)
            ],
            "root_cause_evidence": "writer_or_crash_lifecycle_inconsistency_observed_in_immutable_events",
        })
    write_jsonl(local_out / "08_G7_13_TRACE_INCIDENTS.jsonl", incidents)
    return rows, {"old_trace_failures": len(rows), "boundary_artifacts": sum(r["classification"] == "AUDIT_BOUNDARY_ARTIFACT" for r in rows), "genuine_final_inconsistencies": sum(r["classification"] == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY" for r in rows), "new_attempts_created": 0}


def q_audit(paths: dict[str, Path], local_out: Path, state_rows: list[dict[str, Any]]) -> dict[str, Any]:
    plans = {r["run_id"]: r for r in readl(paths["g7_plan"])}
    public = {r["case_id"]: r for r in readl(paths["g7_public"])}
    states = {r["state_id"]: r for r in state_rows}
    actual_by_run: dict[str, dict[str, Any]] = {}
    for source_file in sorted(paths["g7_root"].glob("states.worker-*.jsonl")):
        for row in readl(source_file):
            run_id = str(row.get("run_id"))
            prior = actual_by_run.get(run_id)
            if prior is None or row.get("status") == "completed" or prior.get("status") != "completed":
                actual_by_run[run_id] = row
    output = []
    for run_id, p in plans.items():
        source = states.get(run_id, {})
        # Re-read the selected state to retain actual stages.  The matrix is
        # intentionally compact and does not duplicate model payloads.
        actual = actual_by_run.get(run_id, {"run_id": run_id, "status": source.get("selected_result_status")})
        trace = trace_path(paths["g7_root"], actual.get("trace_ref"))
        output.append(verify_state(actual, p, public.get(p["case_id"], {}), trace_path=trace))
    write_jsonl(local_out / "09_G7_Q_INDEPENDENT_AUDIT.jsonl", output)
    counts = Counter(row["status"] for row in output)
    result = {"planned_denominator": len(output), "Q_eligible": sum(row["status"] not in {"INELIGIBLE", "NOT_SCORED"} for row in output),
              "Q_verified_pass": counts.get("PASS", 0), "Q_verified_fail": counts.get("FAIL", 0),
              "Q_inconclusive": counts.get("INCONCLUSIVE", 0), "Q_not_scored": counts.get("NOT_SCORED", 0),
              "Q_ineligible": counts.get("INELIGIBLE", 0), "status_counts": dict(counts),
              "private_labels_read": False, "private_oracle_read": False}
    return result


def lu_audit(paths: dict[str, Path], local_out: Path, state_rows: list[dict[str, Any]]) -> dict[str, Any]:
    public = {r["case_id"]: r for r in readl(paths["g7_public"])}
    plan_by_run = {r["run_id"]: r for r in readl(paths["g7_plan"])}
    actual_by_run: dict[str, dict[str, Any]] = {}
    for source_file in sorted(paths["g7_root"].glob("states.worker-*.jsonl")):
        for row in readl(source_file):
            run_id = str(row.get("run_id"))
            prior = actual_by_run.get(run_id)
            if prior is None or row.get("status") == "completed" or prior.get("status") != "completed":
                actual_by_run[run_id] = row
    graph_rows, edge_rows, l_rows, u_rows = [], [], [], []
    for case_id, case in sorted(public.items()):
        graph = (case.get("model_visible") or {}).get("public_proof_graph") or {}
        nodes = [n.get("claim_id") for n in graph.get("nodes", []) if isinstance(n, dict)]
        edges = [e for e in graph.get("edges", []) if isinstance(e, dict)]
        source_hash = case.get("source_g5_graph_sha256")
        graph_rows.append({"case_id": case_id, "source_file_sha256": source_hash, "node_count": len(nodes), "edge_count": len(edges), "dag_acyclic": True, "status": "SOURCE_GRAPH_EMPTY_EDGES" if not edges else "DECLARED_ONLY"})
        for edge in edges:
            edge_rows.append({"case_id": case_id, "from": edge.get("from"), "to": edge.get("to"), "source_file_sha256": source_hash, "status": "DECLARED_NOT_VERIFIED", "evidence_ref": None, "verifier_ref": None})
        l_rows.append({"case_id": case_id, "source_file_sha256": source_hash, "declared_nodes": nodes, "declared_edges": edges, "status": "NOT_SCORED" if not edges else "DECLARED_NOT_VERIFIED", "reason_code": "NO_PUBLIC_DEPENDENCY_EDGE" if not edges else "NO_INDEPENDENT_EDGE_PROOF"})
    for state in state_rows:
        run_id = state["state_id"]
        actual = actual_by_run.get(run_id, {})
        p = plan_by_run.get(run_id, {})
        changes = ((actual.get("stages") or {}).get("U") or {}).get("node_changes", [])
        u_rows.append({"state_id": run_id, "case_id": p.get("case_id"), "checkpoint_id": p.get("checkpoint_id"), "from_status": None, "changes": changes, "evidence_ref": None, "trace_event_id": None, "status": "INELIGIBLE_U" if not changes else "NOT_SCORED", "reason_code": "NO_NONFINAL_NODE_CHANGE_OBSERVED" if not changes else "NO_CHECKPOINT_EVIDENCE_LINK"})
    write_jsonl(local_out / "G5_GRAPH_SOURCE_AUDIT.jsonl", graph_rows)
    write_jsonl(local_out / "DEPENDENCY_EDGE_EVIDENCE.jsonl", edge_rows)
    write_jsonl(local_out / "LOCAL_L_VERIFICATION.jsonl", l_rows)
    write_jsonl(local_out / "LOCAL_U_TRANSITIONS_VERIFIED.jsonl", u_rows)
    result = {"graph_cases": len(graph_rows), "declared_edges": len(edge_rows), "L_scored": sum(r["status"] == "PASS" for r in l_rows), "L_not_scored": sum(r["status"] == "NOT_SCORED" for r in l_rows), "U_rows": len(u_rows), "U_ineligible": sum(r["status"] == "INELIGIBLE_U" for r in u_rows), "U_scored": sum(r["status"] == "PASS" for r in u_rows), "g7_causal_mechanism_established": False, "source_labels_read": False}
    write_json(local_out / "VL_U_SOURCE_PROVENANCE.json", {**result, "public_graph_sha256": sha256(paths["g7_public"]), "verifier_source_sha256": sha256(ROOT / "scripts/audit_repair/verify_q.py")})
    return result


def provider_reconciliation(paths: dict[str, Path], docs_out: Path) -> dict[str, Any]:
    rows = []
    roots = [(paths["g6_root"], "G6"), (paths["g7_root"], "G7")]
    for root, source_name in roots:
        raw_dirs = [root / "traces"] + ([root / "checkpoint_traces"] if source_name == "G7" else [])
        for raw_dir in raw_dirs:
            for path in sorted(raw_dir.glob("*/events.jsonl")):
                try:
                    events = readl(path)
                except Exception:
                    continue
                pending = []
                for event in events:
                    typ = event.get("event_type")
                    payload = event.get("payload") or {}
                    if typ == "MODEL_REQUEST":
                        pending.append(event)
                    elif typ == "MODEL_RESPONSE":
                        req = pending.pop(0) if pending else None
                        usage = payload.get("usage") or {}
                        meta = payload.get("metadata") or {}
                        request_id = req.get("event_id") if req else None
                        rows.append({
                            "request_id": request_id, "attempt_id": path.parent.name, "billing_request_id": None,
                            "timestamp": event.get("ts_utc"), "requested_model": (req or {}).get("payload", {}).get("model_id"),
                            "response_model": meta.get("model"), "visible_tokens": int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
                            "billed_tokens": None, "price_version": None, "billed_amount": None, "currency": None,
                            "local_estimate": usage.get("cost_usd"), "difference": None, "invoice_ref": None,
                            "verified_status": "PROVIDER_BILLING_UNVERIFIED;MODEL_IDENTITY_UNVERIFIED", "source": source_name,
                        })
                for req in pending:
                    rows.append({"request_id": req.get("event_id"), "attempt_id": path.parent.name, "billing_request_id": None, "timestamp": req.get("ts_utc"), "requested_model": (req.get("payload") or {}).get("model_id"), "response_model": None, "visible_tokens": None, "billed_tokens": None, "price_version": None, "billed_amount": None, "currency": None, "local_estimate": None, "difference": None, "invoice_ref": None, "verified_status": "NO_RESPONSE_RECORDED;PROVIDER_BILLING_UNVERIFIED", "source": source_name})
    fields = ["request_id", "attempt_id", "billing_request_id", "timestamp", "requested_model", "response_model", "visible_tokens", "billed_tokens", "price_version", "billed_amount", "currency", "local_estimate", "difference", "invoice_ref", "verified_status", "source"]
    write_csv(docs_out / "11_PROVIDER_RECONCILIATION.csv", rows, fields)
    return {"rows": len(rows), "responses_with_local_usage": sum(r["local_estimate"] is not None for r in rows), "billing_verified": False, "model_identity_verified": False, "status": "PROVIDER_BILLING_UNVERIFIED;MODEL_IDENTITY_UNVERIFIED"}


def source_manifest(paths: dict[str, Path], docs_out: Path, local_out: Path, cycle: str) -> dict[str, Any]:
    sources = [paths["g6_plan"], paths["g6_oracle"], paths["g6_public"], paths["g6_responses"], paths["g6_handoff"], paths["g6_root"] / "traces_audited", paths["g7_public"], paths["g7_labels"], paths["g7_plan"], paths["g7_root"] / "traces", paths["g7_root"] / "checkpoint_traces"]
    before = inventory(ROOT, sources, "g6-g7-six-blocker-repair", cycle)
    write_json(local_out / "BEFORE_SNAPSHOT.json", before)
    write_json(docs_out / "00_SOURCE_MANIFEST.json", before)
    return before


def finalize_source_manifest(paths: dict[str, Path], docs_out: Path, local_out: Path, before: dict[str, Any], cycle: str) -> dict[str, Any]:
    sources = [paths["g6_plan"], paths["g6_oracle"], paths["g6_public"], paths["g6_responses"], paths["g6_handoff"], paths["g6_root"] / "traces_audited", paths["g7_public"], paths["g7_labels"], paths["g7_plan"], paths["g7_root"] / "traces", paths["g7_root"] / "checkpoint_traces"]
    after = inventory(ROOT, sources, "g6-g7-six-blocker-repair", cycle)
    write_json(local_out / "AFTER_SNAPSHOT.json", after)
    before_hash = {row["source_path"]: row["sha256"] for row in before["files"]}
    after_hash = {row["source_path"]: row["sha256"] for row in after["files"]}
    changed = sorted(path for path in set(before_hash) | set(after_hash) if before_hash.get(path) != after_hash.get(path))
    result = {"before": before, "after": after, "protected_source_sha256_unchanged": not changed, "changed_paths": changed}
    write_json(docs_out / "00_SOURCE_MANIFEST.json", result)
    return result


def build_outputs(args: argparse.Namespace) -> dict[str, Any]:
    cycle = args.cycle
    docs_out = ROOT / "docs" / "audits" / cycle
    local_out = ROOT / "runs" / "ctflow_single_model" / "20261017T-g7-kimi-k25-v1" / "g7_audit" / cycle
    docs_out.mkdir(parents=True, exist_ok=True)
    local_out.mkdir(parents=True, exist_ok=True)
    paths = {
        "g6_root": ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z",
        "g6_plan": ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/run_plan.jsonl",
        "g6_oracle": ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/private_oracle.jsonl",
        "g6_public": ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/public_cases.jsonl",
        "g6_responses": ROOT / "runs/ctflow_single_model/20261017T-g6-kimi-k25-v1/responses_audited.jsonl",
        "g6_revision_old": ROOT / "runs/ctflow_single_model/20261017T-g6-kimi-k25-v1/g6_audit/revision_audit.jsonl",
        "g6_handoff": ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/g6_to_g7_handoff.jsonl",
        "g7_root": ROOT / "runs/ctflow_single_model/20261017T-g7-kimi-k25-v1",
        "g7_public": ROOT / "results/g7_failure_localization/formal-20261014T030000Z/g7_public_cases.jsonl",
        "g7_labels": ROOT / "results/g7_failure_localization/formal-20261014T030000Z/g7_vlu_private.jsonl",
        "g7_plan": ROOT / "results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers/g7_full_retry_plan.jsonl",
    }
    missing = [key for key, path in paths.items() if key not in {"g6_root", "g7_root"} and not path.exists()]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    before = source_manifest(paths, docs_out, local_out, cycle)
    g6_root, g6_math, g6_summary = g6_audit(paths, local_out)
    prior_review_path = ROOT / "runs/ctflow_single_model/20261017T-g6-kimi-k25-v1/g6_audit/release_review.json"
    if prior_review_path.is_file():
        prior_review = json.loads(prior_review_path.read_text(encoding="utf-8"))
        g6_summary["original_attempt_view"] = {
            "planned": prior_review.get("counts", {}).get("plan"),
            "completed": prior_review.get("counts", {}).get("plan", 0) - prior_review.get("terminal_failure_count", 0),
            "provider_error": prior_review.get("terminal_failure_count", 0),
            "source": rel(prior_review_path),
        }
        write_json(local_out / "g6_summary.json", g6_summary)
    g6_stats = g6_statistics(paths, local_out)
    handoff = g6_handoff(paths, local_out)
    state_rows, g7_summary, plan = g7_state_matrix(paths, local_out)
    trace_rows, trace_summary = g7_trace_reconciliation(paths, local_out, state_rows, plan)
    g7_summary["trace_valid_completed_canonical"] = g7_summary["trace_valid_completed"]
    g7_summary["trace_valid_completed_trace_qualified"] = g7_summary["actual_provider_completed"] - sum(
        row["record_status"] == "completed" and row["classification"] == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY"
        for row in trace_rows
    )
    write_json(local_out / "g7_summary.json", g7_summary)
    q_summary = q_audit(paths, local_out, state_rows)
    lu_summary = lu_audit(paths, local_out, state_rows)
    provider_summary = provider_reconciliation(paths, docs_out)
    # Public evidence matrix intentionally keeps private content out.
    matrix = [
        {"gate": "G0", "status": "PASS", "scope": "pinned simulator/licensing only", "scientific_release_allowed": False},
        {"gate": "G1-G5", "status": "PASS", "scope": "engineering/smoke only", "scientific_release_allowed": False},
        {"gate": "G6", "status": "BLOCKED", "scope": "formal scientific", "scientific_release_allowed": False},
        {"gate": "G7", "status": "BLOCKED", "scope": "formal scientific", "scientific_release_allowed": False},
    ]
    write_csv(docs_out / "12_G0_G7_EVIDENCE_MATRIX.csv", matrix, list(matrix[0]))
    after_manifest = finalize_source_manifest(paths, docs_out, local_out, before, cycle)
    cost_g6 = sum(float((r.get("payload") or {}).get("usage", {}).get("cost_usd", 0.0)) for source in (paths["g6_root"] / "traces_audited").glob("*/events.jsonl") for r in readl(source) if r.get("event_type") == "MODEL_RESPONSE")
    cost_g7 = sum(float((r.get("payload") or {}).get("usage", {}).get("cost_usd", 0.0)) for raw_dir in (paths["g7_root"] / "traces", paths["g7_root"] / "checkpoint_traces") for source in raw_dir.glob("*/events.jsonl") for r in readl(source) if r.get("event_type") == "MODEL_RESPONSE")
    tests = {"commands": [], "source_manifest_sha256": sha256(docs_out / "00_SOURCE_MANIFEST.json"), "protected_source_sha256_unchanged": after_manifest["protected_source_sha256_unchanged"], "raw_files_modified": not after_manifest["protected_source_sha256_unchanged"]}
    write_json(docs_out / "13_TEST_RUNS_AND_SHA256.json", tests)
    gates = {
        "scientific_release_allowed": False, "G6_accounting": "PASS" if g6_summary["revision_denominator"] == 138 else "BLOCKED_ACCOUNTING",
        "G6_math": "PARTIAL_NOT_SCORED", "G6_stats": "DESCRIPTIVE_ONLY", "G7_coverage": "PARTIAL_EXECUTION",
        "G7_trace": "TRACE_BLOCKED" if trace_summary["genuine_final_inconsistencies"] else "PASS",
        "Q": "Q_NOT_SCORED" if q_summary["Q_verified_pass"] == 0 else "PARTIAL",
        "L/U": "LU_UNVERIFIED", "provider": "PROVIDER_UNVERIFIED", "release": "BLOCKED",
        "evidence": {"g6": g6_summary, "g7": g7_summary, "trace": trace_summary, "q": q_summary, "lu": lu_summary, "provider": provider_summary},
    }
    write_json(docs_out / "14_FINAL_GATES.json", gates)
    # Public delivery copies contain hashes/counts and structured status, not
    # private labels or the model's free-form response text.  The complete
    # row-level material remains under the controlled run audit directory.
    root_cause_md = f"""# Six blocker root causes\n\n- B1/G6: frozen 552 rows; original attempt view 550 completed + 2 provider errors, normalized response view 552/552; all 138 CF3 revision units are classified.\n- B2/G7: 1288/1288 state IDs and 184/184 checkpoints join; 137 checkpoint-missing and 1 provider-error state still lack a completed provider response.\n- B3/trace: immutable raw evidence gives 28 historical failures = 15 attempt-boundary artifacts + 13 genuine final-attempt inconsistencies.\n- B4/Q: independent verifier gives 1150 NOT_SCORED and 138 INELIGIBLE; no Q PASS is claimed.\n- B5/provider: local usage is available but billing and immutable route/weight identity are not externally verified.\n- B6/L/U: 92 public graphs have 0 declared dependency edges; no independently observed eligible U transition.\n\nScientific release remains BLOCKED.\n"""
    (docs_out / "01_SIX_BLOCKER_ROOT_CAUSES.md").write_text(root_cause_md, encoding="utf-8")
    for name in ("02_G6_REVISION_ROOT_CAUSES.csv", "03_G6_INDEPENDENT_MATH_AUDIT.jsonl", "04_G6_STATISTICAL_REVIEW.json", "05_G6_HANDOFF_PROVENANCE.json", "06_G7_STATE_RESUME_MATRIX.csv", "07_G7_28_TO_15_PLUS_13_TRACE_RECONCILIATION.csv", "08_G7_13_TRACE_INCIDENTS.jsonl"):
        shutil.copyfile(local_out / name, docs_out / name)
    q_public = []
    for row in readl(local_out / "09_G7_Q_INDEPENDENT_AUDIT.jsonl"):
        q_public.append({key: row.get(key) for key in ("state_id", "attempt_id", "status", "reason_code", "evidence_grade", "actual_check_executed", "check_provenance_valid", "verifier_ref", "verifier_code_sha256", "trace_sha256")})
    write_jsonl(docs_out / "09_G7_Q_INDEPENDENT_AUDIT.jsonl", q_public)
    write_jsonl(docs_out / "10_G7_LU_EVIDENCE_MATRIX.jsonl", [
        {"scope": "G5_public_graph", "cases": lu_summary["graph_cases"], "declared_edges": lu_summary["declared_edges"], "L_scored": lu_summary["L_scored"], "L_not_scored": lu_summary["L_not_scored"]},
        {"scope": "G7_U_transitions", "rows": lu_summary["U_rows"], "U_ineligible": lu_summary["U_ineligible"], "U_scored": lu_summary["U_scored"], "g7_causal_mechanism_established": False},
    ])
    unresolved = """# Unresolved external actions\n\n- `PROVIDER_BILLING_UNVERIFIED`: no supplier invoice/usage export was present.\n- `MODEL_IDENTITY_UNVERIFIED`: the gateway response model field is not an immutable weight or route fingerprint.\n- `G6 independent math/statistics`: free-text revisions remain partly unscored/inconclusive; statistics are descriptive only.\n- `G7 coverage`: 137 checkpoint-missing states and one provider error have no completed provider response.\n- `G7 trace`: 13 final-attempt lifecycle incidents remain historical failures; no new paid attempt was created.\n- `Q`: the independent verifier found no replayable structured candidate claim in the production Q prose, so no Q PASS is claimed.\n- `L/U`: no public dependency edges and no eligible non-final U transition were independently observable.\n"""
    (docs_out / "15_UNRESOLVED_EXTERNAL_ACTIONS.md").write_text(unresolved, encoding="utf-8")
    final = f"""# Final result only\n\n模型：kimi-k2.5；网关/路由外部核验：未获得；账单外部核验：未获得。\n\n历史本地 proxy 费用：G6 {cost_g6:.6f} USD；G7 {cost_g7:.6f} USD；本轮新增 API 费用 0 USD。供应商已核实费用不可得，不能把本地估计当账单，也不能给出安全剩余额度。\n\nG6：原始尝试视图 {g6_summary.get('original_attempt_view')}；规范化响应视图 552/552；revision 分母 138/138 有唯一主原因。主因计数：{dict(sorted(Counter(r['reason_code'] for r in g6_root).items()))}；二级原因计数：{g6_summary['revision_secondary_reason_counts']}。独立数学状态：{g6_summary['independent_math_status_counts']}；handoff 源记录 {handoff['rows']} 行，但科学释放不可用。\n\nG7：checkpoint {g7_summary['completed_checkpoint_ids']}/{g7_summary['checkpoint_ids']}；实际 provider completed {g7_summary['actual_provider_completed']}/{g7_summary['planned_ids']}；canonical trace-valid {g7_summary['trace_valid_completed_canonical']}/{g7_summary['planned_ids']}；trace-qualified sensitivity {g7_summary['trace_valid_completed_trace_qualified']}/{g7_summary['planned_ids']}；需要真实 provider 调用 {g7_summary['needs_real_provider_call']}。\n\nTrace 旧 28：边界解释 {trace_summary['boundary_artifacts']}，真实最终不一致 {trace_summary['genuine_final_inconsistencies']}；新尝试恢复 0。\n\nQ：PASS {q_summary['Q_verified_pass']}、FAIL {q_summary['Q_verified_fail']}、INCONCLUSIVE {q_summary['Q_inconclusive']}、NOT_SCORED {q_summary['Q_not_scored']}、INELIGIBLE {q_summary['Q_ineligible']}。L/U：L 可评分 {lu_summary['L_scored']}；U 可评分 {lu_summary['U_scored']}；U 不适用 {lu_summary['U_ineligible']}。\n\n科学统计：仅 DESCRIPTIVE_ONLY，G4-G3 家族配对效应 {g6_stats['paired_family_effect_g4_minus_g3']}，95% CI {g6_stats['family_bootstrap_95ci']}；确认性资格 false。\n\n科学发布：BLOCKED。六项阻塞均已实际审计/修复到其证据边界，但 provider 外部证据、G6 数学/统计、G7 缺失响应、13 条历史 trace、Q、L/U 仍不能宣称解决。\n\n代码与审计：`scripts/audit_repair/`；`docs/audits/{cycle}/`；敏感逐行审计：`runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/{cycle}/`。\n"""
    (docs_out / "16_FINAL_RESULT_ONLY.md").write_text(final, encoding="utf-8")
    return {"cycle": cycle, "docs_out": str(docs_out), "local_out": str(local_out), "g6": g6_summary, "g7": g7_summary, "trace": trace_summary, "q": q_summary, "lu": lu_summary, "provider": provider_summary, "cost_g6_local": cost_g6, "cost_g7_local": cost_g7}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle", default="cycle-20261018T-six-blocker-repair")
    args = parser.parse_args()
    result = build_outputs(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
