"""Freeze V9 public tasks and private deterministic truth before any Kimi call."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .claim_ir import ClaimIR
from .common import sha_obj, write_json, write_jsonl
from .math_verifier import verify_claim


def _ir(expression: str, relation: str, domain: str, excerpt: str) -> ClaimIR:
    return ClaimIR("monotonicity", expression, relation, "x", domain, excerpt)


def _case_ir(family: str) -> ClaimIR:
    specs = {
        "F01": ("2*x+1", "increasing", "x>=0"),
        "F02": ("-x**2", "decreasing", "x>=0"),
        "F03": ("x**2", "increasing", "x>=0"),
        "F04": ("3-2*x", "decreasing", "all_real"),
    }
    expression, relation, domain = specs[family]
    return _ir(expression, relation, domain, f"f(x)={expression} is {relation} for {domain}")


def _write_plan(base: Path, protocol: str, cases: list[dict[str, Any]]) -> None:
    plan = {"protocol": protocol, "model_id": "kimi-k2.5", "case_ids": [x.get("case_id", x.get("task_id")) for x in cases], "frozen_at_utc": datetime.now(timezone.utc).isoformat(), "no_midrun_adaptation": protocol.startswith("G6_LLM_ONLY")}
    write_json(base / "plan.json", plan)


def build_g6(base: Path) -> dict[str, Any]:
    base.mkdir(parents=True, exist_ok=True)
    families = ["F01", "F02", "F03", "F04"]
    actions = {"CF1": "REJECT", "CF2": "MAINTAIN", "CF3": "REVISE", "CF4": "UNDETERMINED"}
    cases: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for family in families:
        ir = _case_ir(family)
        proof = verify_claim(ir)
        for cf, expected in actions.items():
            for arm in ("G6_A_G3_GIVEN", "G6_B_G4_GIVEN"):
                arm_tag = "A" if arm.endswith("GIVEN") and arm.startswith("G6_A") else "B"
                case_id = f"V9-G6-{family}-{cf}-ARM{arm_tag}"
                if cf == "CF1":
                    public_claim = f"f(x)={ir.expression} is {'decreasing' if ir.relation == 'increasing' else 'increasing'} for {ir.domain}."
                    intervention = "The sign of the conclusion is reversed while the public expression and domain stay fixed."
                elif cf == "CF2":
                    public_claim = f"f(x)={ir.expression} is {ir.relation} for {ir.domain}."
                    intervention = "Rename x to z consistently; no mathematical content is changed."
                elif cf == "CF3":
                    public_claim = f"f(x)={ir.expression} is {ir.relation} for {ir.domain}."
                    intervention = "The boundary is made explicit; reassess whether the stated strict/non-strict claim needs qualification."
                else:
                    public_claim = f"The public expression is {ir.expression}; its slope sign is withheld for this one case."
                    intervention = "No replacement observation is supplied; decide whether the claim is identifiable."
                public = {
                    "cohort_id": "G6_KIMI_V9_MACHINE_VERIFIABLE",
                    "source_task_id": f"V9-G6-{family}", "case_id": case_id, "family_id": family,
                    "cf_type": cf, "arm_id": arm, "original_problem": f"Determine the monotonicity of the public function f(x)={ir.expression} on {ir.domain}.",
                    "original_claim": public_claim, "intervention_statement": intervention,
                    "public_graph": {"nodes": [{"claim_id": "C1", "statement": public_claim, "evidence_refs": ["public_equation", "public_domain"]}], "edges": [], "version": 1},
                }
                cases.append(public)
                truth.append({
                    "cohort_id": "G6_KIMI_V9_MACHINE_VERIFIABLE", "source_task_id": public["source_task_id"], "case_id": case_id,
                    "claim_ir": ir.to_dict(), "public_proof": proof, "expected_action": expected,
                    "revision_valid": cf == "CF3" and proof["status"] == "PROVEN_TRUE", "truth_key_sent_to_model": False,
                })
    _write_plan(base, "G6_LLM_ONLY_AND_AGENT_SAME_KIMI", cases)
    write_jsonl(base / "public_cases.jsonl", cases)
    write_jsonl(base / "private_truth.jsonl", truth)
    return {"protocol": "G6_KIMI_V9_MACHINE_VERIFIABLE", "public_count": len(cases), "truth_count": len(truth), "truth_sha256": hashlib.sha256((base / "private_truth.jsonl").read_bytes()).hexdigest()}


def build_q(base: Path) -> dict[str, Any]:
    base.mkdir(parents=True, exist_ok=True)
    specs = [("Q01", "2*x+1", "increasing", "x>=0"), ("Q02", "-x**2", "decreasing", "x>=0"), ("Q03", "x**2", "increasing", "x>=0"), ("Q04", "3-2*x", "decreasing", "all_real"), ("Q05", "x**2", "decreasing", "x>=0"), ("Q06", "-x**2", "increasing", "x>=0"), ("Q07", "x+1", "increasing", "all_real"), ("Q08", "2*x+4", "decreasing", "all_real")]
    public, truth = [], []
    for task_id, expression, relation, domain in specs:
        ir = _ir(expression, relation, domain, f"f(x)={expression} is {relation} for {domain}")
        proof = verify_claim(ir)
        row = {"cohort_id": "Q_KIMI_V9_TRUTH_FIRST", "task_id": task_id, "claim_id": f"claim-{task_id}", "public_proposition": ir.source_excerpt, "proposition_dsl": {"expression": expression, "relation": relation, "domain": domain}, "required_action_schema": ["PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN"]}
        public.append(row)
        truth.append({"cohort_id": row["cohort_id"], "task_id": task_id, "claim_ir": ir.to_dict(), "independent_certificate": proof, "expected_status": proof["status"], "truth_key_sent_to_model": False})
    _write_plan(base, "Q_TRUTH_FIRST_INDEPENDENT_MACHINE_ORACLE", public)
    write_jsonl(base / "public_cases.jsonl", public); write_jsonl(base / "private_truth.jsonl", truth)
    return {"protocol": "Q_KIMI_V9_TRUTH_FIRST", "public_count": len(public), "truth_count": len(truth)}


def build_lu(base: Path) -> dict[str, Any]:
    base.mkdir(parents=True, exist_ok=True)
    specs = [("LU01", "2*x+1", "increasing", "x>=0"), ("LU02", "-x**2", "decreasing", "x>=0"), ("LU03", "x**2", "increasing", "x>=0"), ("LU04", "3-2*x", "decreasing", "all_real")]
    public, truth = [], []
    for task_id, expression, relation, domain in specs:
        ir = _ir(expression, relation, domain, f"The public local lemma is f(x)={expression} and should be {relation} on {domain}.")
        control_ir = _ir(expression, "nondecreasing" if relation in {"increasing", "nondecreasing"} else "nonincreasing", domain, ir.source_excerpt)
        real_proof, control_proof = verify_claim(ir), verify_claim(control_ir)
        row = {"cohort_id": "LU_V9_PROSPECTIVE", "task_id": task_id, "checkpoint_id": f"checkpoint-{task_id}", "checkpoint_nodes": [{"node_id": "V1", "statement": "A public initial observation is available."}, {"node_id": "U1", "statement": ir.source_excerpt, "status": "NON_FINAL"}], "control_public_claim": "Re-evaluate the same public non-final lemma without an intervention.", "real_intervention": {"kind": "REAL", "evidence": "The public derivative sign was independently measured on the allowed interval; update U1 only."}, "sham_intervention": {"kind": "SHAM", "evidence": "A randomized formatting token; it contains no mathematical information."}}
        public.append(row)
        truth.append({"cohort_id": row["cohort_id"], "task_id": task_id, "checkpoint_id": row["checkpoint_id"], "intervention_ir": ir.to_dict(), "control_ir": control_ir.to_dict(), "real_status": real_proof["status"], "control_status": control_proof["status"], "sham_status": control_proof["status"], "truth_key_sent_to_model": False})
    _write_plan(base, "LU_U_SHARED_CHECKPOINT_CONTROL_REAL_SHAM", public)
    write_jsonl(base / "public_cases.jsonl", public); write_jsonl(base / "private_truth.jsonl", truth)
    return {"protocol": "LU_V9_PROSPECTIVE", "checkpoints": len(public), "truth_count": len(truth)}


def build_g7(base: Path) -> dict[str, Any]:
    base.mkdir(parents=True, exist_ok=True)
    specs = [("G7A", "2*x+1", "increasing", "x>=0"), ("G7B", "-x**2", "decreasing", "x>=0"), ("G7C", "x**2", "increasing", "x>=0"), ("G7D", "3-2*x", "decreasing", "all_real")]
    public, truth = [], []
    for task_id, expression, relation, domain in specs:
        ir = _ir(expression, relation, domain, f"The hidden final law candidate concerns f(x)={expression} on {domain}.")
        proof = verify_claim(ir)
        row = {"cohort_id": "G7_KIMI_V9_FINAL", "task_id": task_id, "checkpoint_id": f"g7-checkpoint-{task_id}", "initial_public_observation": "Only the public measurement protocol is supplied; the private final Y is not supplied.", "public_graph": {"nodes": [{"node_id": "V", "statement": "Inspect the public variable relation."}, {"node_id": "L", "statement": "State candidate local edges from public evidence."}, {"node_id": "U", "statement": "Update one non-final local lemma."}], "edges": [["V", "L"], ["L", "U"]]}, "stages": ["D0", "D1_V", "D2_VL", "D3_VLU"], "private_Y_injected": False}
        public.append(row)
        truth.append({"cohort_id": row["cohort_id"], "task_id": task_id, "claim_ir": ir.to_dict(), "proof": proof, "expected_relation": relation, "expected_graph_edges": [["V", "L"], ["L", "U"]], "private_Y_injected": False})
    _write_plan(base, "G7_D0_D1_D2_D3_PUBLIC_CHECKPOINT_FORK", public)
    write_jsonl(base / "public_cases.jsonl", public); write_jsonl(base / "private_truth.jsonl", truth)
    return {"protocol": "G7_KIMI_V9_FINAL", "checkpoint_count": len(public), "planned_stage_records": len(public) * 4}


def build_agent_comparison(base: Path) -> dict[str, Any]:
    base.mkdir(parents=True, exist_ok=True)
    public = []
    for i, expression in enumerate(["2*x+1", "-x**2", "x**2", "3-2*x"], 1):
        public.append({"cohort_id": "AGENT_COMPARISON_KIMI_V9", "task_id": f"AC{i}", "public_problem": f"Select a next public measurement for f(x)={expression}; the action budget is two measurements.", "initial_observation": {"x": 0, "y": 1 if expression == "2*x+1" else 0}, "observations_after_first_action": {"x": 1, "y": 3 if expression == "2*x+1" else -1 if expression == "-x**2" else 1 if expression == "x**2" else 1}, "allowed_actions": [{"x": 0}, {"x": 1}, {"x": 2}], "budget": 2})
    _write_plan(base, "SAME_KIMI_LLM_ONLY_FROZEN_PLAN_VS_AGENT_ADAPTIVE", public)
    write_jsonl(base / "public_cases.jsonl", public)
    return {"protocol": "AGENT_COMPARISON_KIMI_V9", "task_count": len(public), "truth_key": "none_private_oracle_not_needed"}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); root = args.out
    result = {"g6": build_g6(root / "g6"), "q": build_q(root / "q"), "lu": build_lu(root / "lu"), "g7": build_g7(root / "g7"), "agent_comparison": build_agent_comparison(root / "agent_comparison"), "model_id": "kimi-k2.5"}
    write_json(root / "BUILD_RESULT.json", result); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
