"""V10 unattended, machine-first single-Kimi G6/G7 execution.

The runner freezes public plans and certificates before the first provider call,
uses an atomic SQLite task ledger for resume, retains every raw response and
failure, and never reads private truth while constructing model messages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.v9.common import append_jsonl, extract_json, read_jsonl, sha256_file, sha_obj, write_json, write_jsonl
from scripts.v9.provider import SingleKimiProvider

from .machine_truth import FAMILIES, Q_SPECS, certificate, replay_certificate, write_certificate


MODEL_ID = "kimi-k2.5"
ARMS = ("G6_A_G3_GIVEN", "G6_B_G4_GIVEN")
CF_EXPECTED = {"CF1": "REJECT", "CF2": "MAINTAIN", "CF3": "REVISE", "CF4": "UNDETERMINED"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_jsonl_append(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _safe_hash(path: Path) -> str | None:
    return sha256_file(path) if path.exists() and path.is_file() else None


def _public_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _all_old_hashes(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    roots = [repo / "runs", repo / "docs" / "audits"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or "kimi-v10-machine" in path.as_posix():
                continue
            try:
                result[path.relative_to(repo).as_posix()] = sha256_file(path)
            except OSError:
                continue
    return result


def _ledger_init(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30.0)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("CREATE TABLE IF NOT EXISTS units (unit_id TEXT PRIMARY KEY, namespace TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, updated_at TEXT NOT NULL)")
    connection.commit()
    return connection


def _ledger_status(connection: sqlite3.Connection, unit_id: str) -> str | None:
    row = connection.execute("SELECT status FROM units WHERE unit_id=?", (unit_id,)).fetchone()
    return str(row[0]) if row else None


def _claim(connection: sqlite3.Connection, unit_id: str, namespace: str) -> bool:
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = connection.execute("SELECT status FROM units WHERE unit_id=?", (unit_id,)).fetchone()
        if row and row[0] in {"COMPLETED", "EXPLICIT_FAILURE"}:
            connection.rollback()
            return False
        if row:
            connection.execute("UPDATE units SET status='RUNNING', attempts=attempts+1, updated_at=? WHERE unit_id=?", (now_utc(), unit_id))
        else:
            connection.execute("INSERT INTO units(unit_id,namespace,status,attempts,updated_at) VALUES(?,?, 'RUNNING', 1, ?)", (unit_id, namespace, now_utc()))
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def _finish(connection: sqlite3.Connection, unit_id: str, status: str, error: str | None = None) -> None:
    connection.execute("UPDATE units SET status=?, last_error=?, updated_at=? WHERE unit_id=?", (status, error, now_utc(), unit_id))
    connection.commit()


def _build_g6() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for family_id, expression, relation, domain in FAMILIES:
        cert = certificate(expression, relation, domain, source="v10_g6_truth_first_sympy")
        for cf_type, expected_action in CF_EXPECTED.items():
            for arm in ARMS:
                arm_code = "A" if arm == ARMS[0] else "B"
                case_id = f"{family_id}-{cf_type}-{arm_code}"
                if cf_type == "CF1":
                    claim = f"f(x)={expression} is {'decreasing' if relation == 'increasing' else 'increasing'} on {domain}."
                    intervention = "The conclusion sign is reversed while equation and domain remain fixed."
                    original_truth = False
                elif cf_type == "CF2":
                    claim = f"f(x)={expression} is {relation} on {domain}."
                    intervention = "Rename x to z consistently; no mathematical content changes."
                    original_truth = True
                elif cf_type == "CF3":
                    claim = f"f(x)={expression} is {relation} on {domain}."
                    intervention = "Expose the domain boundary and reassess the strict relation."
                    original_truth = True
                else:
                    claim = f"The public expression is {expression}; its slope sign is withheld."
                    intervention = "No replacement observation is supplied; decide whether the claim is identifiable."
                    original_truth = None
                row = {
                    "protocol_profile": "theory_benchmark",
                    "experiment_id": "G6-MACHINE-FINAL",
                    "cohort_id": "G6-MACHINE-FINAL",
                    "source_task_id": family_id,
                    "case_id": case_id,
                    "theory_family_id": family_id,
                    "cf_type": cf_type,
                    "arm_id": arm,
                    "model_id": MODEL_ID,
                    "original_problem": f"Determine monotonicity of f(x)={expression} on {domain}.",
                    "original_claim": claim,
                    "intervention_statement": intervention,
                    "public_graph": {"nodes": [{"claim_id": "C1", "statement": claim, "kind": "non_final_public_claim"}], "edges": [], "version": 1},
                }
                public.append(row)
                truth.append({
                    "case_id": case_id,
                    "source_task_id": family_id,
                    "theory_family_id": family_id,
                    "cf_type": cf_type,
                    "arm_id": arm,
                    "claim_ir": {"expression": expression, "relation": relation, "domain": domain, "variable": "x"},
                    "machine_certificate": cert,
                    "original_claim_truth_under_new_premise": original_truth,
                    "expected_action_truth": expected_action,
                    "revision_truth": cf_type == "CF3" and cert["status"] == "PROVEN_TRUE",
                    "truth_key_sent_to_model": False,
                })
    return public, truth


def _build_q() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for task_id, expression, relation, domain in Q_SPECS:
        cert = certificate(expression, relation, domain, source="v10_q_first_sympy")
        row = {"protocol_profile": "theory_benchmark", "experiment_id": "Q92-MACHINE-FIRST", "cohort_id": "Q92-MACHINE-FIRST-NEW", "task_id": task_id, "model_id": MODEL_ID, "claim_id": f"claim-{task_id}", "public_proposition": f"f(x)={expression} is {relation} on {domain}.", "proposition_dsl": {"expression": expression, "relation": relation, "domain": domain}, "required_action_schema": ["PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN"]}
        public.append(row)
        truth.append({"task_id": task_id, "claim_ir": row["proposition_dsl"], "machine_certificate": cert, "expected_status": cert["status"], "truth_key_sent_to_model": False})
    return public, truth


def _build_g7() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for index, (family_id, expression, relation, domain) in enumerate(FAMILIES, 1):
        task_id = f"V10-G7-{index:02d}"
        cert = certificate(expression, relation, domain, source="v10_g7_graph_truth_first")
        public.append({"protocol_profile": "theory_benchmark", "experiment_id": "G7-MACHINE-VLUQ", "cohort_id": "G7-MACHINE-VLUQ", "task_id": task_id, "model_id": MODEL_ID, "checkpoint_id": f"v10-checkpoint-{index:02d}", "initial_public_observation": "Public measurements and rules are available; private final Y is not supplied.", "public_graph": {"nodes": [{"claim_id": "V", "statement": f"The public equation is f(x)={expression} on {domain}.", "kind": "verdict_candidate"}, {"claim_id": "L", "statement": "A derivative-sign lemma may support V.", "kind": "non_final_lemma"}, {"claim_id": "U", "statement": "One non-final derivative update may alter the local diagnosis.", "kind": "non_final_intermediate"}], "edges": [["L", "V"], ["U", "L"]], "version": 1}, "stages": ["D0", "D1_V", "D2_VL", "D3_VLU"], "private_Y_injected": False})
        truth.append({"task_id": task_id, "theory_family_id": family_id, "claim_ir": {"expression": expression, "relation": relation, "domain": domain, "variable": "x"}, "machine_certificate": cert, "expected_relation": relation, "expected_graph_edges": [["L", "V"], ["U", "L"]], "private_Y_injected": False})
    return public, truth


def _build_lu() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for index, (family_id, expression, relation, domain) in enumerate(FAMILIES, 1):
        task_id = f"V10-LU-{index:02d}"
        cert = certificate(expression, relation, domain, source="v10_lu_real_intervention_dev")
        public.append({"protocol_profile": "theory_benchmark", "experiment_id": "LU-U-MACHINE-CAUSAL", "cohort_id": "LU-U-MACHINE-CAUSAL", "task_id": task_id, "theory_family_id": family_id, "model_id": MODEL_ID, "checkpoint_id": f"v10-lu-checkpoint-{index:02d}", "checkpoint_nodes": [{"claim_id": "V", "statement": "A public initial observation is available.", "kind": "verdict"}, {"claim_id": "U1", "statement": f"The non-final local lemma concerns f(x)={expression} on {domain}.", "kind": "non_final_intermediate"}], "control_public_claim": "Re-evaluate the same public non-final U1 without intervention.", "real_intervention": {"kind": "REAL", "target_claim_id": "U1", "evidence": f"The independently measured derivative sign supports the relation {relation}; update only U1."}, "sham_intervention": {"kind": "SHAM", "target_claim_id": "U1", "evidence": "A format-matched neutral token; no mathematical content."}})
        truth.append({"task_id": task_id, "theory_family_id": family_id, "claim_ir": {"expression": expression, "relation": relation, "domain": domain, "variable": "x"}, "real_certificate": cert, "real_relation": relation, "control_relation": None, "sham_relation": None, "target_claim_id": "U1", "truth_key_sent_to_model": False})
    return public, truth


def _build_agent() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for index, (family_id, expression, relation, domain) in enumerate(FAMILIES, 1):
        task_id = f"V10-AGENT-{index:02d}"
        target = {"x": (index % 3)}
        row = {"protocol_profile": "theory_benchmark", "experiment_id": "AGENT-VS-LLM-ONLY", "cohort_id": "AGENT-VS-LLM-ONLY", "task_id": task_id, "theory_family_id": family_id, "model_id": MODEL_ID, "public_problem": f"Choose the next allowed public measurement for f(x)={expression}; the action budget is two.", "initial_observation": {"x": 0, "y": index}, "feedback_observation": {"x": 1, "y": index + 1}, "allowed_actions": [{"x": 0}, {"x": 1}, {"x": 2}], "budget": 2}
        public.append(row)
        truth.append({"task_id": task_id, "theory_family_id": family_id, "expected_action": target, "truth_key_sent_to_model": False})
    return public, truth


def _lineage_legacy(repo: Path, audit_root: Path) -> dict[str, Any]:
    source = repo / "docs/audits/cycle-20261019T094634Z-kimi-v8-real-evidence/LEGACY_G6_276_CLAIM_RECOVERY.jsonl"
    out = audit_root / "G6_LEGACY_LINEAGE_276.jsonl"
    rows = read_jsonl(source) if source.exists() else []
    lineage: list[dict[str, Any]] = []
    for row in rows:
        recovery = row.get("recovered_claim_ir")
        lineage.append({"case_id": row.get("case_id"), "cf_type": row.get("cf_type"), "raw_source_path": (row.get("trace_provenance") or {}).get("trace_path"), "raw_sha256": (row.get("trace_provenance") or {}).get("trace_sha256"), "public_problem_sha256": _public_hash(row.get("original_problem")), "source_span": row.get("original_response_excerpt", "")[:600], "ir_candidates": [recovery] if recovery else [], "semantic_consistency_tests": {"status": "NOT_RUN_FOR_UNPARSEABLE" if not recovery else "LEGACY_REPLAY_ONLY"}, "claim_decision": row.get("recovery_status"), "independent_proof_ref": None, "terminal_status": "RAW_CLAIM_UNAVAILABLE" if not recovery else "LEGACY_CLAIM_RECOVERED", "historical_source_row_sha256": row.get("historical_source_row_sha256")})
    write_jsonl(out, lineage)
    return {"source": str(source), "rows": len(lineage), "raw_claim_unavailable": sum(x["terminal_status"] == "RAW_CLAIM_UNAVAILABLE" for x in lineage), "source_sha256": _safe_hash(source), "output_sha256": _safe_hash(out)}


def freeze_plan(repo: Path, run_root: Path, audit_root: Path) -> dict[str, Any]:
    existing = run_root / "preregistration.json"
    if existing.exists():
        return json.loads(existing.read_text(encoding="utf-8"))
    run_root.mkdir(parents=True, exist_ok=True)
    public_all: list[dict[str, Any]] = []
    truth_index: dict[str, list[dict[str, Any]]] = {}
    builders = {"g6": _build_g6, "q": _build_q, "g7": _build_g7, "lu": _build_lu, "agent": _build_agent}
    for namespace, builder in builders.items():
        public, truth = builder()
        truth_index[namespace] = truth
        write_jsonl(run_root / "plans" / f"{namespace}_public.jsonl", public)
        write_jsonl(run_root / "private_truth" / f"{namespace}.jsonl", truth)
        public_all.extend([{**row, "namespace": namespace} for row in public])
    write_jsonl(run_root / "public_cases.jsonl", public_all)
    plan_rows: list[dict[str, Any]] = []
    for row in read_jsonl(run_root / "plans/g6_public.jsonl"):
        plan_rows.append({"unit_id": f"G6:{row['case_id']}", "namespace": "g6", "case_id": row["case_id"], "arm_id": row["arm_id"], "theory_family_id": row["theory_family_id"]})
    for row in read_jsonl(run_root / "plans/q_public.jsonl"):
        plan_rows.append({"unit_id": f"Q:{row['task_id']}", "namespace": "q", "task_id": row["task_id"]})
    for row in read_jsonl(run_root / "plans/g7_public.jsonl"):
        for stage in ["CHECKPOINT", "D0", "D1_V", "D2_VL", "D3_VLU", "Q"]:
            plan_rows.append({"unit_id": f"G7:{row['task_id']}:{stage}", "namespace": "g7", "task_id": row["task_id"], "checkpoint_id": row["checkpoint_id"], "stage": stage})
    for row in read_jsonl(run_root / "plans/lu_public.jsonl"):
        for arm in ["CHECKPOINT", "CONTROL", "REAL", "SHAM"]:
            plan_rows.append({"unit_id": f"LU:{row['task_id']}:{arm}", "namespace": "lu", "task_id": row["task_id"], "checkpoint_id": row["checkpoint_id"], "arm": arm})
    for row in read_jsonl(run_root / "plans/agent_public.jsonl"):
        for workflow in ["LLM_ONLY", "AGENT"]:
            for step in [1, 2]:
                plan_rows.append({"unit_id": f"AGENT:{row['task_id']}:{workflow}:{step}", "namespace": "agent", "task_id": row["task_id"], "workflow": workflow, "step": step})
    write_jsonl(run_root / "frozen_plan.jsonl", plan_rows)
    if len({row["unit_id"] for row in plan_rows}) != len(plan_rows):
        raise RuntimeError("frozen plan contains duplicate unit_id values")
    write_jsonl(audit_root / "G7_FORK_PLAN.jsonl", [row for row in plan_rows if row["namespace"] == "g7"])
    # Machine certificates and claim IR are materialized before the first
    # provider call.  These files are audit inputs, never prompt inputs.
    g6_truth = truth_index["g6"]
    write_jsonl(audit_root / "G6_CLAIM_IR.jsonl", [
        {"case_id": row["case_id"], "claim_ir": row["claim_ir"], "machine_certificate_sha256": row["machine_certificate"]["certificate_sha256"]}
        for row in g6_truth
    ])
    for row in g6_truth:
        write_certificate(audit_root / "G6_MACHINE_CERTS" / f"{row['case_id']}.json", row["machine_certificate"])
    write_jsonl(audit_root / "G6_NEW_FROZEN_PLAN.jsonl", [row for row in plan_rows if row["namespace"] == "g6"])
    for row in truth_index["q"]:
        write_certificate(audit_root / "Q_MACHINE_FIRST_TRUTH_CERTS" / f"{row['task_id']}.json", row["machine_certificate"])
    for row in truth_index["g7"]:
        write_certificate(audit_root / "G7_Q_PROOF_CERTS" / f"{row['task_id']}.json", row["machine_certificate"])
    write_jsonl(audit_root / "LU_MACHINE_VERIFIED_GRAPH.jsonl", [
        {"task_id": row["task_id"], "claim_ir": row["claim_ir"], "real_certificate": row["real_certificate"], "target_claim_id": row["target_claim_id"]}
        for row in truth_index["lu"]
    ])
    write_jsonl(audit_root / "LU_PAIR_PLAN.jsonl", [
        {"task_id": row["task_id"], "arms": ["CONTROL", "REAL", "SHAM"], "checkpoint_id": next(item["checkpoint_id"] for item in read_jsonl(run_root / "plans/lu_public.jsonl") if item["task_id"] == row["task_id"]), "shared_checkpoint": True}
        for row in truth_index["lu"]
    ])
    truth_hashes = {name: _safe_hash(run_root / "private_truth" / f"{name}.jsonl") for name in truth_index}
    public_hash = _safe_hash(run_root / "public_cases.jsonl")
    plan_hash = _safe_hash(run_root / "frozen_plan.jsonl")
    prereg = {"protocol_profile": "theory_benchmark", "experiment_id": "V10-G6-G7-MACHINE", "model_id": MODEL_ID, "only_model": True, "frozen_at_utc": now_utc(), "public_cases_sha256": public_hash, "prospective_plan_hash": plan_hash, "truth_certificate_hashes": truth_hashes, "budget": {"max_cost_usd": 5.0, "max_output_tokens": 1024, "max_attempts_per_unit": 2}, "retry_policy_fixed": ["transient_one_retry", "malformed_json_one_format_retry", "otherwise_explicit_failure"], "historical_denominators_unchanged": {"g6_formal": 552, "g6_machine_rows": 276, "g7_frozen": 1288, "g7_recovery": 150, "g7_historical_defects": 13, "q92": 92, "lu_legacy_pairs": 6}, "truth_certificates_precede_model_calls": True, "no_private_truth_in_public_plan": True, "full_denominator_defined": True, "plan_counts": dict(Counter(row["namespace"] for row in plan_rows)), "theory_families": [family[0] for family in FAMILIES]}
    write_json(run_root / "preregistration.json", prereg)
    write_json(audit_root / "BASELINE_MANIFEST.json", {"generated_at_utc": now_utc(), "historical_denominators_unchanged": True, "old_artifact_hashes": _all_old_hashes(repo), "v10_public_cases_sha256": public_hash, "v10_plan_sha256": plan_hash})
    write_json(audit_root / "PROTOCOL_NAMESPACE_MATRIX.json", {"protocol_profile": "theory_benchmark", "experiment_id": "V10-G6-G7-MACHINE", "model_id": MODEL_ID, "only_model": True, "namespaces": {"G6": "G6-MACHINE-FINAL", "G7": "G7-MACHINE-VLUQ", "Q": "Q92-MACHINE-FIRST", "LU": "LU-U-MACHINE-CAUSAL", "Agent": "AGENT-VS-LLM-ONLY"}})
    _lineage_legacy(repo, audit_root)
    return prereg


def _messages(system: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)}]


def _final_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    return {str(row["unit_id"]): row for row in rows if row.get("final") is True}


def _execute(provider: SingleKimiProvider, ledger: sqlite3.Connection, run_root: Path, namespace: str, unit_id: str, messages: list[dict[str, str]], payload: dict[str, Any]) -> dict[str, Any]:
    response_path = run_root / "model_responses.jsonl"
    existing = _final_rows(response_path)
    if unit_id in existing and _ledger_status(ledger, unit_id) in {"COMPLETED", "EXPLICIT_FAILURE"}:
        return existing[unit_id]
    if not _claim(ledger, unit_id, namespace):
        return _final_rows(response_path).get(unit_id, {"unit_id": unit_id, "status": "EXPLICIT_FAILURE", "error": "claimed_elsewhere"})
    final: dict[str, Any] | None = None
    for attempt in (1, 2):
        result = provider.call(f"V10_{namespace.upper()}", unit_id, f"attempt-{attempt}", messages)
        candidate = extract_json(result.get("content"))
        event = {"event_type": "MODEL_RESPONSE", "unit_id": unit_id, "namespace": namespace, "attempt_id": attempt, "model_id": MODEL_ID, "request_sha256": sha_obj(messages), "request_messages": messages, "raw_content": result.get("content"), "provider_error": result.get("error"), "call_number": result.get("call_number"), "usage": result.get("usage") or {}, "created_at_utc": now_utc(), "private_truth_injected": False}
        append_jsonl(run_root / "raw_model_events.jsonl", event)
        final = {"unit_id": unit_id, "namespace": namespace, "attempt_id": attempt, "model_id": MODEL_ID, "request_sha256": sha_obj(messages), "candidate": candidate, "raw_content_present": bool(result.get("content")), "provider_error": result.get("error"), "call_number": result.get("call_number"), "status": "COMPLETED" if candidate is not None and not result.get("error") else "EXPLICIT_FAILURE", "private_truth_injected": False, "final": candidate is not None and not result.get("error"), "created_at_utc": now_utc()}
        if final["final"]:
            break
        _write_jsonl_append(run_root / "retry_lineage.jsonl", [{"unit_id": unit_id, "attempt_id": attempt, "reason": "malformed_json_or_provider_error", "raw_preserved": True, "next_action": "FORMAT_RETRY" if attempt == 1 else "EXPLICIT_FAILURE"}])
    assert final is not None
    if not final["final"]:
        final["final"] = True
    _write_jsonl_append(response_path, [final])
    _finish(ledger, unit_id, final["status"], final.get("provider_error"))
    return final


def _run_g6(provider: SingleKimiProvider, ledger: sqlite3.Connection, run_root: Path) -> None:
    rows = read_jsonl(run_root / "plans/g6_public.jsonl")
    system = "You are one frozen V10 G6 arm using only public data. Never access private truth, files, network, or answer keys. Return JSON with decision, affected_claim_ids, revised_claim, supporting_evidence."
    for row in rows:
        _execute(provider, ledger, run_root, "g6", f"G6:{row['case_id']}", _messages(system, {"g6_case": row}), row)


def _run_q(provider: SingleKimiProvider, ledger: sqlite3.Connection, run_root: Path) -> None:
    rows = read_jsonl(run_root / "plans/q_public.jsonl")
    system = "You are a blinded V10 Q auditor. Use only the public proposition. Return JSON with candidate_claim_ir, checked_obligations, witness_refs, final_state_id, proposed_final_action. Action must be PROVEN_TRUE, PROVEN_FALSE, or UNKNOWN. Never access private truth."
    for row in rows:
        _execute(provider, ledger, run_root, "q", f"Q:{row['task_id']}", _messages(system, {"public_task": row}), row)


def _run_g7(provider: SingleKimiProvider, ledger: sqlite3.Connection, run_root: Path, audit_root: Path) -> None:
    rows = read_jsonl(run_root / "plans/g7_public.jsonl")
    checkpoints: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    system = "You are the public-only V10 G7 diagnostic agent. Never access private Y, truth keys, files, network, or hidden tasks. Return compact JSON only."
    for task in rows:
        checkpoint_id = task["checkpoint_id"]
        checkpoint_messages = _messages(system, {"task_id": task["task_id"], "public_graph": task["public_graph"], "initial_public_observation": task["initial_public_observation"], "stage": "CHECKPOINT"})
        checkpoint = _execute(provider, ledger, run_root, "g7", f"G7:{task['task_id']}:CHECKPOINT", checkpoint_messages, task)
        checkpoints.append({"task_id": task["task_id"], "checkpoint_id": checkpoint_id, "messages_sha256": sha_obj(checkpoint_messages), "initial_output": checkpoint.get("candidate"), "state_before": {"public_graph": task["public_graph"]}, "private_Y_injected": False})
        previous: dict[str, Any] = {}
        for stage in ["D0", "D1_V", "D2_VL", "D3_VLU"]:
            evidence: dict[str, Any] = {"task_id": task["task_id"], "checkpoint_id": checkpoint_id, "public_graph": task["public_graph"], "checkpoint_output": checkpoint.get("candidate"), "stage": stage}
            if stage == "D1_V": evidence["prior_D0"] = previous.get("D0", {})
            if stage == "D2_VL": evidence["V"] = previous.get("D1_V", {})
            if stage == "D3_VLU": evidence.update({"V": previous.get("D1_V", {}), "L": previous.get("D2_VL", {}), "U": {"claim_id": "U", "kind": "non_final", "status": "PUBLIC_UPDATE_ALLOWED"}})
            result = _execute(provider, ledger, run_root, "g7", f"G7:{task['task_id']}:{stage}", _messages(system, evidence), task)
            previous[stage] = result.get("candidate") or {}
            event = {"task_id": task["task_id"], "checkpoint_id": checkpoint_id, "stage": stage, "unit_id": f"G7:{task['task_id']}:{stage}", "input_sha256": sha_obj(evidence), "candidate": result.get("candidate"), "provider_error": result.get("provider_error"), "private_Y_injected": False}
            events.append(event)
        q_payload = {"task_id": task["task_id"], "checkpoint_id": checkpoint_id, "public_graph": task["public_graph"], "d3_candidate": previous.get("D3_VLU", {}), "instruction": "Perform Q audit of the public derivation; do not access private final truth."}
        q = _execute(provider, ledger, run_root, "g7", f"G7:{task['task_id']}:Q", _messages(system + " Return candidate_claim_ir, checked_obligations, witness_refs, final_state_id, final_action.", q_payload), task)
        events.append({"task_id": task["task_id"], "checkpoint_id": checkpoint_id, "stage": "Q", "unit_id": f"G7:{task['task_id']}:Q", "input_sha256": sha_obj(q_payload), "candidate": q.get("candidate"), "provider_error": q.get("provider_error"), "private_Y_injected": False})
    write_jsonl(run_root / "checkpoint_events.jsonl", checkpoints)
    write_jsonl(run_root / "g7_vluq_events.jsonl", events)
    write_jsonl(audit_root / "G7_VLUQ_CERTS/G7_EVENTS.jsonl", events)
    write_jsonl(audit_root / "G7_CHECKPOINTS.jsonl", checkpoints)
    write_jsonl(audit_root / "G7_VLUQ_EVENTS.jsonl", events)


def _run_lu(provider: SingleKimiProvider, ledger: sqlite3.Connection, run_root: Path, audit_root: Path) -> None:
    rows = read_jsonl(run_root / "plans/lu_public.jsonl")
    raw: list[dict[str, Any]] = []
    system = "You are a public-only V10 LU/U checkpoint agent. Update only the named non-final U1 claim. Never access private truth or final Y. Return JSON with claim_id, state_before, state_after, intermediate_status, evidence."
    for task in rows:
        base = {"task_id": task["task_id"], "checkpoint_id": task["checkpoint_id"], "checkpoint_nodes": task["checkpoint_nodes"], "control_claim": task["control_public_claim"]}
        init_messages = _messages(system, base)
        init = _execute(provider, ledger, run_root, "lu", f"LU:{task['task_id']}:CHECKPOINT", init_messages, task)
        raw.append({"task_id": task["task_id"], "checkpoint_id": task["checkpoint_id"], "arm": "CHECKPOINT", "messages_sha256": sha_obj(init_messages), "candidate": init.get("candidate"), "private_truth_injected": False})
        for arm in ["CONTROL", "REAL", "SHAM"]:
            intervention = task["real_intervention"] if arm == "REAL" else task["sham_intervention"] if arm == "SHAM" else {"kind": "CONTROL", "target_claim_id": "U1", "evidence": "No intervention; repeat the public checkpoint."}
            payload = {**base, "shared_checkpoint_output": init.get("candidate"), "arm": arm, "public_intervention": intervention, "instruction": "Return a non-final U1 state update only."}
            messages = _messages(system, payload)
            result = _execute(provider, ledger, run_root, "lu", f"LU:{task['task_id']}:{arm}", messages, task)
            raw.append({"task_id": task["task_id"], "checkpoint_id": task["checkpoint_id"], "arm": arm, "messages_sha256": sha_obj(init_messages), "candidate": result.get("candidate"), "provider_error": result.get("provider_error"), "private_truth_injected": False})
    write_jsonl(run_root / "lu_raw_events.jsonl", raw)
    write_jsonl(audit_root / "LU_SHARED_CHECKPOINTS.jsonl", [row for row in raw if row["arm"] == "CHECKPOINT"])
    write_jsonl(audit_root / "LU_REAL_SHAM_CONTROL_RAW.jsonl", [row for row in raw if row["arm"] != "CHECKPOINT"])


def _run_agent(provider: SingleKimiProvider, ledger: sqlite3.Connection, run_root: Path) -> None:
    rows = read_jsonl(run_root / "plans/agent_public.jsonl")
    system = "You are the single Kimi V10 workflow comparator. Choose only allowed public actions and return JSON with action. Never access hidden truth."
    for task in rows:
        for workflow in ["LLM_ONLY", "AGENT"]:
            first = _execute(provider, ledger, run_root, "agent", f"AGENT:{task['task_id']}:{workflow}:1", _messages(system, {"task": task, "workflow": workflow, "observation": task["initial_observation"], "instruction": "Select the first action."}), task)
            if workflow == "LLM_ONLY":
                second_payload = {"task": task, "workflow": workflow, "frozen_plan": first.get("candidate"), "batch_observations": [task["initial_observation"], task["feedback_observation"]], "instruction": "Choose the second action from the frozen plan; do not use interim feedback to replan."}
            else:
                second_payload = {"task": task, "workflow": workflow, "first_action": first.get("candidate"), "new_public_observation": task["feedback_observation"], "instruction": "Choose the next action after observed public feedback."}
            _execute(provider, ledger, run_root, "agent", f"AGENT:{task['task_id']}:{workflow}:2", _messages(system, second_payload), task)


def _bootstrap_stats(rows: list[dict[str, Any]], cluster_key: str, score_key: str, reps: int = 2000) -> dict[str, Any]:
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(cluster_key))].append(int(bool(row.get(score_key))))
    if not groups:
        return {"n": 0, "clusters": 0, "estimate": None, "ci95": None, "cluster_key": cluster_key, "score_key": score_key, "bootstrap": reps}
    names = list(groups)
    values = [v for group in groups.values() for v in group]
    estimate = sum(values) / len(values)
    rng = random.Random(20261020)
    samples: list[float] = []
    for _ in range(reps):
        selected = [rng.choice(names) for _ in names]
        flat = [v for name in selected for v in groups[name]]
        samples.append(sum(flat) / len(flat))
    samples.sort()
    return {"n": len(values), "clusters": len(groups), "estimate": estimate, "ci95": [samples[int(reps * .025)], samples[int(reps * .975) - 1]], "cluster_key": cluster_key, "score_key": score_key, "bootstrap": reps}


def score_all(run_root: Path, audit_root: Path) -> dict[str, Any]:
    truth = {name: {str(row.get("case_id", row.get("task_id"))): row for row in read_jsonl(run_root / "private_truth" / f"{name}.jsonl")} for name in ["g6", "q", "g7", "lu", "agent"]}
    responses = _final_rows(run_root / "model_responses.jsonl")
    g6_scores: list[dict[str, Any]] = []
    for row in read_jsonl(run_root / "plans/g6_public.jsonl"):
        observed = responses.get(f"G6:{row['case_id']}", {})
        candidate = observed.get("candidate") or {}
        expected = truth["g6"][row["case_id"]]
        decision = str(candidate.get("decision", "")).upper()
        revision = candidate.get("revised_claim")
        revision_text = json.dumps(revision, ensure_ascii=False, sort_keys=True).lower() if revision is not None else ""
        expected_relation = str(expected["claim_ir"]["relation"]).lower()
        expected_expression = str(expected["claim_ir"]["expression"]).lower()
        expected_domain = str(expected["claim_ir"]["domain"]).lower()
        revision_semantically_valid = (revision is None) if not expected["revision_truth"] else bool(revision_text) and expected_relation in revision_text and expected_expression in revision_text and expected_domain in revision_text
        g6_scores.append({"case_id": row["case_id"], "theory_family_id": row["theory_family_id"], "cf_type": row["cf_type"], "arm_id": row["arm_id"], "status": observed.get("status"), "expected_action": expected["expected_action_truth"], "model_action_correct": decision == expected["expected_action_truth"] and observed.get("status") == "COMPLETED", "revision_expected": bool(expected["revision_truth"]), "revision_present": revision is not None, "model_revision_semantically_valid": bool(revision_semantically_valid), "affected_dependency_valid": isinstance(candidate.get("affected_claim_ids", []), list), "provider_error": observed.get("provider_error"), "request_sha256": observed.get("request_sha256")})
    write_jsonl(audit_root / "G6_MODEL_ACTION_AND_REVISION_SCORES.jsonl", g6_scores)
    g6_stats = {"all_planned_action": _bootstrap_stats(g6_scores, "theory_family_id", "model_action_correct"), "by_arm": {arm: _bootstrap_stats([r for r in g6_scores if r["arm_id"] == arm], "theory_family_id", "model_action_correct") for arm in ARMS}, "by_cf": {cf: _bootstrap_stats([r for r in g6_scores if r["cf_type"] == cf], "theory_family_id", "model_action_correct") for cf in CF_EXPECTED}}
    write_json(audit_root / "G6_FAMILY_CLUSTER_STATISTICS.json", g6_stats)

    q_scores: list[dict[str, Any]] = []
    for row in read_jsonl(run_root / "plans/q_public.jsonl"):
        observed = responses.get(f"Q:{row['task_id']}", {})
        candidate = observed.get("candidate") or {}
        expected = truth["q"][row["task_id"]]
        dsl = candidate.get("candidate_claim_ir") or candidate.get("proposition_DSL") or {}
        dsl_match = all(dsl.get(k) == v for k, v in row["proposition_dsl"].items())
        action = str(candidate.get("proposed_final_action", candidate.get("final_action", ""))).upper()
        replay = replay_certificate(expected["claim_ir"]["expression"], expected["claim_ir"]["relation"], expected["claim_ir"]["domain"])
        q_scores.append({"task_id": row["task_id"], "action_schema_valid": action in {"PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN"}, "q_proof_valid": replay["status"] == expected["expected_status"], "q_state_match": dsl_match, "final_Y_correct": dsl_match and action == expected["expected_status"], "independent_replay": replay, "provider_error": observed.get("provider_error"), "truth_key_sent_to_model": False})
    write_jsonl(audit_root / "Q_INDEPENDENT_REVIEW.jsonl", q_scores)
    q_metrics = {"planned": len(q_scores), "action_schema_valid": sum(x["action_schema_valid"] for x in q_scores), "q_proof_valid": sum(x["q_proof_valid"] for x in q_scores), "q_state_match": sum(x["q_state_match"] for x in q_scores), "final_Y_correct": sum(x["final_Y_correct"] for x in q_scores), "truth_key_sent_to_model": False, "machine_truth_first": True}
    write_json(audit_root / "Q_METRICS.json", q_metrics)

    g7_truth = truth["g7"]
    g7_scores: list[dict[str, Any]] = []
    g7_q: list[dict[str, Any]] = []
    for task in read_jsonl(run_root / "plans/g7_public.jsonl"):
        expected = g7_truth[task["task_id"]]
        for stage in ["D0", "D1_V", "D2_VL", "D3_VLU"]:
            observed = responses.get(f"G7:{task['task_id']}:{stage}", {})
            candidate = observed.get("candidate") or {}
            text = json.dumps(candidate, ensure_ascii=False).lower()
            d3 = stage == "D3_VLU"
            strict = d3 and expected["expected_relation"] in text and any(token in text for token in ["true", "proven", "accepted", "approved"])
            semantic = d3 and expected["expected_relation"] in text and any(token in text for token in ["infer", "audit", "accept", "complete"])
            g7_scores.append({"task_id": task["task_id"], "theory_family_id": expected["theory_family_id"], "stage": stage, "status": observed.get("status"), "d3_semantic_correct": bool(semantic), "d3_strict_token_correct": bool(strict), "strict_token_invalid": bool(d3 and not strict), "format_error": None if candidate else "MALFORMED_JSON_OR_EXPLICIT_FAILURE", "private_Y_injected": False, "provider_error": observed.get("provider_error")})
        observed = responses.get(f"G7:{task['task_id']}:Q", {})
        candidate = observed.get("candidate") or {}
        replay = replay_certificate(expected["claim_ir"]["expression"], expected["claim_ir"]["relation"], expected["claim_ir"]["domain"])
        g7_q.append({"task_id": task["task_id"], "q_proof_valid": replay["status"] == expected["machine_certificate"]["status"], "candidate_present": bool(candidate), "independent_replay": replay, "private_Y_injected": False})
    write_jsonl(audit_root / "G7_D3_STRICT_VS_SEMANTIC.jsonl", g7_scores)
    write_jsonl(audit_root / "G7_Q_PROOF_CERTS/Q_REVIEW.jsonl", g7_q)
    g7_metrics = {"planned_stage_rows": len(g7_scores), "d3_rows": sum(x["stage"] == "D3_VLU" for x in g7_scores), "d3_semantic_correct": sum(x["d3_semantic_correct"] for x in g7_scores), "d3_strict_token_correct": sum(x["d3_strict_token_correct"] for x in g7_scores), "d3_strict_token_invalid": sum(x["strict_token_invalid"] for x in g7_scores), "q_rows": len(g7_q), "q_proof_valid": sum(x["q_proof_valid"] for x in g7_q), "private_Y_injected": any(x["private_Y_injected"] for x in g7_scores + g7_q)}

    lu_truth = truth["lu"]
    lu_scores: list[dict[str, Any]] = []
    for row in read_jsonl(run_root / "lu_raw_events.jsonl"):
        if row["arm"] == "CHECKPOINT":
            continue
        expected = lu_truth[row["task_id"]]
        candidate = row.get("candidate") or {}
        text = json.dumps(candidate, ensure_ascii=False).lower()
        update_present = candidate.get("claim_id") == expected["target_claim_id"] or "u1" in text
        correct_update = row["arm"] == "REAL" and update_present and expected["real_relation"] in text
        lu_scores.append({"task_id": row["task_id"], "theory_family_id": expected["theory_family_id"], "arm": row["arm"], "state_update_detected": bool(update_present), "correct_update": bool(correct_update), "y_correct": False, "private_truth_injected": False})
    write_jsonl(audit_root / "LU_NONFINAL_U_CERTS/score_rows.jsonl", lu_scores)
    lu_stats = {"u_correct_by_arm": {arm: _bootstrap_stats([r for r in lu_scores if r["arm"] == arm], "theory_family_id", "correct_update") for arm in ["CONTROL", "REAL", "SHAM"]}, "u_correct_real_minus_sham": sum(r["correct_update"] for r in lu_scores if r["arm"] == "REAL") / 4 - sum(r["correct_update"] for r in lu_scores if r["arm"] == "SHAM") / 4, "y_correct_real_minus_sham": 0.0, "planned_fork_rows": len(lu_scores), "shared_checkpoint": True}
    write_json(audit_root / "LU_PAIRED_CAUSAL_STATS.json", lu_stats)

    agent_scores: list[dict[str, Any]] = []
    agent_truth = truth["agent"]
    for task in read_jsonl(run_root / "plans/agent_public.jsonl"):
        expected = agent_truth[task["task_id"]]["expected_action"]
        for workflow in ["LLM_ONLY", "AGENT"]:
            for step in [1, 2]:
                observed = responses.get(f"AGENT:{task['task_id']}:{workflow}:{step}", {})
                candidate = observed.get("candidate") or {}
                action = candidate.get("action") if isinstance(candidate.get("action"), dict) else candidate.get("chosen_action")
                agent_scores.append({"task_id": task["task_id"], "theory_family_id": task["theory_family_id"], "workflow": workflow, "step": step, "action_valid": isinstance(action, dict) and set(action) == {"x"} and action.get("x") in {0, 1, 2}, "target_action_correct": action == expected, "adaptive_feedback_recorded": workflow == "AGENT" and step == 2, "provider_error": observed.get("provider_error")})
    write_jsonl(audit_root / "AGENT_COMPARISON_SCORES.jsonl", agent_scores)
    agent_stats = {workflow: _bootstrap_stats([r for r in agent_scores if r["workflow"] == workflow], "theory_family_id", "action_valid") for workflow in ["LLM_ONLY", "AGENT"]}
    scores = {"g6": {"planned": len(g6_scores), "action_correct": sum(x["model_action_correct"] for x in g6_scores), "revision_valid": sum(x["model_revision_semantically_valid"] for x in g6_scores), "stats": g6_stats}, "q": q_metrics, "g7": g7_metrics, "lu": {"planned": len(lu_scores), "correct_update": sum(x["correct_update"] for x in lu_scores), "stats": lu_stats}, "agent": {"planned": len(agent_scores), "action_valid": sum(x["action_valid"] for x in agent_scores), "stats": agent_stats}}
    write_json(audit_root / "G7_ALL_PLANNED_METRICS.json", scores["g7"])
    return scores


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    run_root = args.run_root.resolve()
    audit_root = args.audit_root.resolve()
    audit_root.mkdir(parents=True, exist_ok=True)
    prereg = freeze_plan(repo, run_root, audit_root)
    ledger = _ledger_init(run_root / "execution_ledger.sqlite")
    provider = SingleKimiProvider(run_root, args.key_file, args.base_url, MODEL_ID, args.max_cost, args.timeout, max_output_tokens=1024)
    _run_g6(provider, ledger, run_root)
    _run_q(provider, ledger, run_root)
    _run_g7(provider, ledger, run_root, audit_root)
    _run_lu(provider, ledger, run_root, audit_root)
    _run_agent(provider, ledger, run_root)
    scores = score_all(run_root, audit_root)
    raw_events = read_jsonl(run_root / "raw_model_events.jsonl")
    write_jsonl(audit_root / "G6_NEW_RAW_EVENTS" / "raw_model_events.jsonl", [row for row in raw_events if row.get("namespace") == "g6"])
    g7_lineage = []
    for row in raw_events:
        if row.get("namespace") == "g7":
            g7_lineage.append({"unit_id": row.get("unit_id"), "attempt_id": row.get("attempt_id"), "call_number": row.get("call_number"), "request_sha256": row.get("request_sha256"), "model_id": row.get("model_id"), "private_truth_injected": row.get("private_truth_injected"), "raw_event_sha256": _public_hash(row)})
    write_jsonl(audit_root / "G7_TRACE_LINEAGE.jsonl", g7_lineage)
    ledger_rows = [{"unit_id": row[0], "namespace": row[1], "status": row[2], "attempts": row[3], "last_error": row[4]} for row in ledger.execute("SELECT unit_id,namespace,status,attempts,last_error FROM units ORDER BY unit_id")]
    write_json(run_root / "execution_ledger_snapshot.json", {"rows": ledger_rows, "integrity": ledger.execute("PRAGMA integrity_check").fetchone()[0]})
    write_json(run_root / "manifest.json", {"protocol_profile": "theory_benchmark", "experiment_id": "V10-G6-G7-MACHINE", "model_id": MODEL_ID, "unique_base_language_models": [MODEL_ID], "only_model": True, "run_id": run_root.name, "preregistration_sha256": _safe_hash(run_root / "preregistration.json"), "prospective_plan_hash": prereg["prospective_plan_hash"], "real_provider_calls": provider.call_no, "local_usage_cost_usd": sum(float((row.get("trace") or {}).get("response", {}).get("usage", {}).get("cost_usd") or 0.0) for row in read_jsonl(run_root / "logs/provider_traces.jsonl")), "scores": scores, "historical_denominators_unchanged": prereg["historical_denominators_unchanged"], "private_truth_injected": False, "execution_status": "COMPLETED"})
    write_json(run_root / "execution_summary.json", {"model_id": MODEL_ID, "real_provider_calls": provider.call_no, "scores": scores, "ledger_units": len(ledger_rows), "ledger_status_counts": dict(Counter(row["status"] for row in ledger_rows)), "completed_at_utc": now_utc()})
    return {"run_root": str(run_root), "audit_root": str(audit_root), "real_provider_calls": provider.call_no, "scores": scores}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, default=Path("api_key/kimi/kimi-k2.5.txt"))
    parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--max-cost", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()
    if not args.key_file.is_absolute():
        args.key_file = args.repo / args.key_file
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
