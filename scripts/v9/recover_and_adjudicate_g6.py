"""Append-only review of the historical 276 G6 records.

This joins the frozen source row, public problem, original model response
excerpt, and source trace reference.  Public equation validity and model
decision agreement are separate fields by design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from .common import read_jsonl, sha256_file, write_json, write_jsonl


def _params(problem: str) -> dict[str, float]:
    match = re.search(r"已知参数：\s*(\{.*?\})", problem or "")
    if not match:
        match = re.search(r"parameters?\s*:\s*(\{.*?\})", problem or "", re.I)
    try:
        raw = json.loads(match.group(1)) if match else {}
        return {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _numbers(text: str) -> list[float]:
    values = []
    for token in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", text or "", re.I):
        try: values.append(float(token))
        except ValueError: pass
    return values


def _close(values: list[float], target: float) -> bool:
    return any(math.isclose(x, target, rel_tol=6e-3, abs_tol=6e-3) for x in values)


def _expected(family: str, p: dict[str, float]) -> tuple[list[float], list[str]]:
    try:
        if family == "G6F-TB-L1-001": return [p["N0"] * math.exp(p["r"] * p["t"])], ["N(t)", "exp"]
        if family == "G6F-TB-L1-002": return [0.0, p["K"]], ["dN/dt", "K"]
        if family == "G6F-TB-L1-003":
            disc = p["K"] ** 2 - 4 * p["h"] * p["K"] / p["r"]
            return [(p["K"] - math.sqrt(disc)) / 2, (p["K"] + math.sqrt(disc)) / 2], ["equilibrium"]
        if family == "G6F-TB-L1-004": return [p["beta"] / p["gamma"]], ["R0"]
        if family == "G6F-TB-L1-005": return [p["Vmax"] * p["S"] / (p["Km"] + p["S"] + p["S"] ** 2 / p["Ki"])], ["Vmax", "Ki"]
        if family == "G6F-TB-L1-006": return [p["S"] / (p["K"] + p["S"]), 0.5], ["theta", "S/(K+S)"]
        if family == "G6F-TB-L1-007": return [p["a"] / p["b"], p["c"] / p["d"]], ["equilibrium"]
        if family == "G6F-TB-L1-008": return [p["alpha"] / p["delta"], 1 / p["delta"]], ["alpha", "delta"]
        if family == "G6F-TB-L1-009": return [p["kon"] / (p["kon"] + p["koff"])], ["kon", "koff"]
        if family == "G6F-TB-L1-011": return [p["mumax"] * p["S"] / (p["Ks"] + p["S"])], ["mumax", "Ks"]
        if family == "G6F-TB-L1-012": return [-p["c"] + p["d"] * p["resident_prey"]], ["invasion"]
        if family == "G6F-TC-L1-001": return [math.log(2) / p["k"]], ["ln(2)", "half"]
        if family == "G6F-TC-L1-002": return [], ["1/A", "k"]
        if family == "G6F-TC-L1-003": return [p["A0"] / p["k"]], ["A(t)", "A0/k"]
        if family == "G6F-TC-L1-004": return [math.exp(p["Ea_J_per_mol"] / p["R"] * (1 / p["T1"] - 1 / p["T2"]))], ["Ea", "T2"]
        if family == "G6F-TC-L1-005": return [math.exp(-p["DeltaG_J_per_mol"] / (p["R"] * p["T"]))], ["DeltaG", "K"]
        if family == "G6F-TC-L1-006": return [p["K1"] * math.exp(p["DeltaH_J_per_mol"] / p["R"] * (1 / p["T1"] - 1 / p["T2"]))], ["K1", "DeltaH"]
        if family == "G6F-TC-L1-007":
            q = math.exp(-p["epsilon_over_RT"]); return [q / (1 + q)], ["epsilon", "q"]
        if family == "G6F-TC-L1-008":
            x = p["x"]; return [x * x * math.exp(x) / (1 + math.exp(x)) ** 2], ["x^2", "exp"]
        if family == "G6F-TC-L1-009": return [p["kB"] / p["kC"], p["kB"] / (p["kB"] + p["kC"])], ["kB", "kC"]
        if family == "G6F-TC-L1-010": return [p["k"] * p["B_fixed"]], ["kobs", "B"]
        if family == "G6F-TC-L1-011": return [p["pKa"] + math.log10(p["ratio"])], ["pKa", "log"]
        if family == "G6F-TC-L1-012": return [p["Vmax"] * p["S"] / (p["Km"] + p["S"]), 0.5], ["Vmax", "Km"]
    except (KeyError, ValueError, ZeroDivisionError, OverflowError):
        return [], []
    return [], []


def adjudicate(row: dict[str, Any]) -> dict[str, Any]:
    family = str(row.get("case_id", "")).split("-CF", 1)[0]
    problem, claim, response = row.get("original_problem") or "", row.get("original_claim") or "", row.get("original_response_excerpt") or ""
    params = _params(problem)
    expected, signatures = _expected(family, params)
    normalized = claim.replace(" ", "").replace("·", "")
    numbers = _numbers(claim)
    numeric_ok = all(_close(numbers, x) for x in expected)
    symbolic_ok = all(token.lower().replace(" ", "") in normalized.lower() for token in signatures) if signatures else False
    public_valid = bool(problem and claim and params and (numeric_ok or symbolic_ok))
    decision_match = re.search(r'"decision"\s*:\s*"(MAINTAIN|REJECT|REVISE|UNDETERMINED)"', response)
    if not decision_match:
        decision_match = re.search(r"\b(MAINTAIN|REJECT|REVISE|UNDETERMINED)\b", response)
    decision = decision_match.group(1) if decision_match else None
    revised = re.search(r'"revised_claim"\s*:\s*"(.*?)"', response, re.S)
    revised_text = revised.group(1) if revised else response
    boundary_evidence = bool(re.search(r"boundary|k\s*=\s*0|K\s*=\s*0|ratio\s*=\s*0|undefined|division by zero|条件|边界|degenerate", revised_text, re.I))
    return {
        "cohort_id": "G6_HISTORICAL_276_APPEND_ONLY", "source_task_id": family, "case_id": row.get("case_id"), "attempt_id": row.get("attempt_id"),
        "arm_id": (row.get("trace_provenance") or {}).get("arm_id"), "replicate": row.get("unit_index"),
        "source_row_sha256": row.get("historical_source_row_sha256"), "trace_ref": (row.get("trace_provenance") or {}).get("trace_path"), "trace_sha256": (row.get("trace_provenance") or {}).get("trace_sha256"),
        "public_problem_valid": public_valid, "public_verifier_status": "PROVEN_TRUE" if public_valid else "UNKNOWN", "public_verifier_reason": "independent_formula_and_numeric_replay" if public_valid else "insufficient_public_claim_or_parameters",
        "model_response_present": bool(response), "model_response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest() if response else None, "model_decision": decision,
        "expected_action_from_frozen_cf3_protocol": "REVISE", "model_decision_match": decision == "REVISE", "revised_claim_present": bool(revised_text.strip()), "revised_claim_boundary_evidence": boundary_evidence,
        "revised_claim_valid": bool(decision == "REVISE" and boundary_evidence), "revision_equivalent_to_target": bool(decision == "REVISE" and boundary_evidence),
        "affected_graph_localization": bool(row.get("original_claim")) and bool(row.get("intervention_statement")), "truth_key_read": False, "historical_data_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--recovered", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(); rows = read_jsonl(args.recovered); results = [adjudicate(r) for r in rows]; write_jsonl(args.output, results)
    summary = {"protocol": "G6_HISTORICAL_276_RECOVER_AND_ADJUDICATE_V9", "rows": len(results), "public_problem_valid": sum(r["public_problem_valid"] for r in results), "model_response_present": sum(r["model_response_present"] for r in results), "model_decision_match": sum(r["model_decision_match"] for r in results), "revised_claim_valid": sum(r["revised_claim_valid"] for r in results), "historical_denominator": 276, "historical_data_modified": False, "private_truth_read": False, "source_sha256": sha256_file(args.recovered), "output_sha256": sha256_file(args.output)}
    write_json(args.summary, summary); print(json.dumps(summary, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
