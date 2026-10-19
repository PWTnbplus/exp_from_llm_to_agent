"""Freeze all V8 prospective public cohorts and private truth before API use."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.v8.claim_ir import ClaimIR
from scripts.v8.prove_exact import prove_claim


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ir(expression: str, relation: str, domain: str) -> dict[str, Any]:
    return ClaimIR(
        kind="monotonicity",
        relation=relation,
        expression=expression,
        variable="x",
        domain=domain,
        source_excerpt=f"f(x)={expression} is {relation} for {domain}",
    ).to_dict()


def _proof(ir: dict[str, Any]) -> dict[str, Any]:
    return prove_claim(ClaimIR(**ir))


def build_g6(root: Path, dirname: str = "prospective_g6") -> dict[str, Any]:
    families = [
        ("V8F01", "2*x+1", "increasing", "x>=0"),
        ("V8F02", "-x**2", "nonincreasing", "x>=0"),
        ("V8F03", "x**2", "nondecreasing", "x>=0"),
        ("V8F04", "3-2*x", "decreasing", "all_real"),
    ]
    action_text = {
        "CF1": "Replace the signed slope or coefficient with its opposite sign while keeping the original conclusion unchanged.",
        "CF2": "Rename x to z consistently in the equation, domain, and conclusion; change no mathematical content.",
        "CF3": "Weaken the domain condition to include the boundary x=0 and reassess the original strict/non-strict claim.",
        "CF4": "Hide the sign of the slope parameter and provide no replacement observation; assess this one instance only.",
    }
    expected = {"CF1": "REJECT", "CF2": "MAINTAIN", "CF3": "REVISE", "CF4": "UNDETERMINED"}
    public: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for family_id, expression, relation, domain in families:
        original_ir = _ir(expression, relation, domain)
        original_proof = _proof(original_ir)
        for cf in ("CF1", "CF2", "CF3", "CF4"):
            for arm in ("G6_A_G3_GIVEN", "G6_B_G4_GIVEN"):
                arm_tag = "A" if arm == "G6_A_G3_GIVEN" else "B"
                case_id = f"V8-G6-{family_id}-{cf}-ARM{arm_tag}"
                original_claim = f"f(x)={expression} is {relation} for {domain}."
                public.append({
                    "case_id": case_id,
                    "family_id": family_id,
                    "cf_type": cf,
                    "arm_id": arm,
                    "original_problem": f"Verify the monotonicity of f(x)={expression} on {domain} using an exact derivative argument.",
                    "original_claim": original_claim,
                    "intervention_statement": action_text[cf],
                    "public_proof_graph": {
                        "nodes": [
                            {"claim_id": "C1", "statement": original_claim, "evidence_refs": ["public_equation", "public_domain"]},
                            {"claim_id": "C2", "statement": "The intervention changes only the stated public condition.", "evidence_refs": ["intervention_statement"]},
                        ],
                        "edges": [["C1", "C2"]],
                        "version": 1,
                    },
                })
                truth.append({
                    "case_id": case_id,
                    "family_id": family_id,
                    "cf_type": cf,
                    "arm_id": arm,
                    "original_claim_ir": original_ir,
                    "original_proof_status": original_proof["status"],
                    "expected_action": expected[cf],
                    "revised_claim_valid": cf == "CF3" and original_proof["status"] == "PROVEN_TRUE",
                    "source": "V8_PRECOMPUTED_SYMPY_CERTIFICATE",
                })
    return _freeze(root / dirname, "V8_G6_PROSPECTIVE", public, truth, {
        "families": len(families), "cases": len(public), "arms": ["G6_A_G3_GIVEN", "G6_B_G4_GIVEN"]
    })


def build_q(root: Path) -> dict[str, Any]:
    specs = [
        ("Q01", "2*x+1", "increasing", "x>=0"),
        ("Q02", "-x**2", "nonincreasing", "x>=0"),
        ("Q03", "x**2", "nondecreasing", "x>=0"),
        ("Q04", "3-2*x", "decreasing", "all_real"),
        ("Q05", "x/2+4", "increasing", "all_real"),
        ("Q06", "-x/3+1", "decreasing", "all_real"),
        ("Q07", "x**3", "increasing", "all_real"),
        ("Q08", "-x**3", "decreasing", "all_real"),
    ]
    public, truth = [], []
    for task_id, expression, relation, domain in specs:
        ir = _ir(expression, relation, domain)
        proof = _proof(ir)
        public.append({
            "task_id": task_id,
            "claim_id": f"{task_id}-C1",
            "proposition_dsl": {"kind": "monotonicity", "expression": expression, "relation": relation, "domain": domain},
            "public_evidence": {"equation": f"f(x)={expression}", "domain": domain},
            "required_fields": ["claim_id", "proposition_DSL", "premise_refs", "quantifier", "domain", "verification_intent", "evidence_refs", "proposed_final_action"],
        })
        truth.append({"task_id": task_id, "claim_id": f"{task_id}-C1", "claim_ir": ir, "independent_proof": proof, "expected_status": proof["status"]})
    return _freeze(root / "prospective_q", "Q_V8_TRUTH_FIRST_PROSPECTIVE", public, truth, {"tasks": len(public), "truth_process_before_provider": True})


def build_lu(root: Path) -> dict[str, Any]:
    specs = [
        ("LU01", "x**2", "nondecreasing", "-x**2", "nonincreasing"),
        ("LU02", "2*x+1", "increasing", "-2*x+1", "decreasing"),
        ("LU03", "x**3", "increasing", "-x**3", "decreasing"),
        ("LU04", "x/2+4", "increasing", "-x/2+4", "decreasing"),
    ]
    public, truth = [], []
    for task_id, control_expr, control_rel, intervention_expr, intervention_rel in specs:
        control_ir = _ir(control_expr, control_rel, "all_real" if task_id in {"LU02", "LU03", "LU04"} else "x>=0")
        intervention_ir = _ir(intervention_expr, intervention_rel, control_ir["domain"])
        public.append({
            "task_id": task_id,
            "claim_id": f"{task_id}-U1",
            "checkpoint_nodes": [
                {"claim_id": f"{task_id}-V1", "statement": f"f(x)={control_expr} is {control_rel}", "kind": "premise"},
                {"claim_id": f"{task_id}-L1", "statement": "The derivative sign is the local verification lemma.", "kind": "lemma"},
                {"claim_id": f"{task_id}-U1", "statement": "The non-final monotonicity status is the update target.", "kind": "intermediate"},
                {"claim_id": f"{task_id}-Y1", "statement": "Final conclusion is evaluated only after the fork.", "kind": "final"},
            ],
            "control_public_claim": {"expression": control_expr, "relation": control_rel, "domain": control_ir["domain"]},
            "real_intervention": {"intervention_id": f"{task_id}-REAL", "statement": f"Replace the public slope structure with f(x)={intervention_expr} and update U1."},
            "sham_intervention": {"intervention_id": f"{task_id}-SHAM", "statement": "Rename an irrelevant evidence label only; preserve the equation and U1."},
        })
        truth.append({
            "task_id": task_id,
            "claim_id": f"{task_id}-U1",
            "control_ir": control_ir,
            "intervention_ir": intervention_ir,
            "control_status": _proof(control_ir)["status"],
            "real_status": _proof(intervention_ir)["status"],
            "sham_status": _proof(control_ir)["status"],
            "source": "V8_PRECOMPUTED_SYMPY_CERTIFICATE",
        })
    return _freeze(root / "prospective_lu", "LU_U_V8_SHARED_CHECKPOINT_RANDOMIZED", public, truth, {"tasks": len(public), "arms": ["CONTROL", "REAL", "SHAM"], "random_seed": 20261019})


def build_g7(root: Path) -> dict[str, Any]:
    specs = [
        ("G7-01", "2*x+1", "increasing", "x>=0"),
        ("G7-02", "-x**2", "nonincreasing", "x>=0"),
        ("G7-03", "x**2", "nondecreasing", "x>=0"),
        ("G7-04", "3-2*x", "decreasing", "all_real"),
    ]
    public, truth = [], []
    for task_id, expression, relation, domain in specs:
        ir = _ir(expression, relation, domain)
        proof = _proof(ir)
        public.append({
            "task_id": task_id,
            "graph_id": f"{task_id}-NEW-GRAPH",
            "nodes": [
                {"claim_id": f"{task_id}-V", "kind": "verdict", "statement": f"f(x)={expression} is {relation} on {domain}"},
                {"claim_id": f"{task_id}-L", "kind": "lemma", "statement": "A derivative-sign lemma connects the equation to the verdict."},
                {"claim_id": f"{task_id}-U", "kind": "intermediate", "statement": "The update target is the non-final derivative status."},
                {"claim_id": f"{task_id}-Y", "kind": "final", "statement": "Return a final decision after checking the public graph."},
            ],
            "public_equation": f"f(x)={expression}",
            "public_domain": domain,
            "diagnostic_stages": ["D0", "D1_V", "D2_VL", "D3_VLU"],
        })
        truth.append({"task_id": task_id, "graph_id": f"{task_id}-NEW-GRAPH", "claim_ir": ir, "proof": proof, "expected_final_action": "MAINTAIN"})
    return _freeze(root / "prospective_g7", "G7_V8_NEW_PROSPECTIVE_VLLUQ", public, truth, {"tasks": len(public), "diagnostic_stages": ["D0", "D1_V", "D2_VL", "D3_VLU"], "not_retroactive": True})


def _freeze(path: Path, protocol_id: str, public: list[dict[str, Any]], truth: list[dict[str, Any]], extra: dict[str, Any]) -> dict[str, Any]:
    path.mkdir(parents=True, exist_ok=True)
    public_sha = _write_jsonl(path / "public_cases.jsonl", public)
    truth_sha = _write_jsonl(path / "truth_key.jsonl", truth)
    plan = {
        "protocol_id": protocol_id,
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "public_cases": len(public),
        "public_sha256": public_sha,
        "truth_key_sha256": truth_sha,
        "truth_key_created_before_provider_calls": True,
        "truth_key_sent_to_model": False,
        "private_truth_isolation": True,
        "model_id": "kimi-k2.5",
        **extra,
    }
    (path / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    plans = {"g6": build_g6(args.run), "q": build_q(args.run), "lu": build_lu(args.run), "g7": build_g7(args.run)}
    (args.run / "cohort_freeze_manifest.json").write_text(json.dumps(plans, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plans, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

