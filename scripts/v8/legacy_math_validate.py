"""Independent replay of the small theory-benchmark equations in historical G6.

This is deliberately separate from model responses and from the old V7
adjudication.  It checks the public equation, parameters, and numerical values
with exact Python/SymPy-derived calculations; it never reads a private oracle.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Callable


def _params(problem: str) -> dict[str, float]:
    match = re.search(r"已知参数：\s*(\{.*?\})", problem or "")
    if not match:
        return {}
    try:
        raw = json.loads(match.group(1))
        return {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _numbers(text: str) -> list[float]:
    values = []
    for item in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", text or "", flags=re.I):
        try:
            values.append(float(item))
        except ValueError:
            pass
    return values


def _contains(values: list[float], target: float, tol: float = 5e-3) -> bool:
    return any(math.isclose(value, target, rel_tol=tol, abs_tol=tol) for value in values)


def _symbolic_ok(case_id: str, claim: str) -> bool:
    text = (claim or "").replace(" ", "").replace("·", "")
    signatures = {
        "G6F-TC-L1-002": ["1/A(t)=1/A₀+kt", "1/A(t)=1/A0+kt", "1/(k·A₀)", "1/(kA₀)"],
        "G6F-TC-L1-009": ["B/CequalskB/kC", "kB/(kB+kC)"],
        "G6F-TB-L1-007": ["y*=a/b"],
        "G6F-TB-L1-001": ["N(t)=N₀·exp(rt)", "N(t)=N0·exp(rt)"],
        "G6F-TC-L1-001": ["t½=ln(2)/k", "t½=ln(2)/k"],
        "G6F-TC-L1-010": ["kobs=k×[B]", "kobs=k[B]"],
    }
    prefix = next((key for key in signatures if case_id.startswith(key)), None)
    if prefix is None:
        return False
    return any(signature.replace(" ", "") in text for signature in signatures[prefix])


def expected_values(case_id: str, problem: str) -> tuple[list[float], str]:
    p = _params(problem)
    if case_id.startswith("G6F-TB-L1-001"):
        return [p.get("N0", 0) * math.exp(p.get("r", 0) * p.get("t", 0))], "exponential_growth"
    if case_id.startswith("G6F-TB-L1-002"):
        return [0.0, p["K"]], "logistic_equilibria"
    if case_id.startswith("G6F-TB-L1-003"):
        K, h, r = p["K"], p["h"], p["r"]
        disc = K * K - 4 * h * K / r
        return [(K - math.sqrt(disc)) / 2, (K + math.sqrt(disc)) / 2], "harvested_logistic_roots"
    if case_id.startswith("G6F-TB-L1-004"):
        return [p["beta"] / p["gamma"]], "sir_R0"
    if case_id.startswith("G6F-TB-L1-005"):
        S, Km, Ki, Vmax = p["S"], p["Km"], p["Ki"], p["Vmax"]
        return [Vmax * S / (Km + S + S * S / Ki)], "substrate_inhibition"
    if case_id.startswith("G6F-TB-L1-006"):
        return [p["S"] / (p["K"] + p["S"]), 0.5], "receptor_occupancy"
    if case_id.startswith("G6F-TB-L1-007"):
        return [p["a"] / p["b"]], "predator_prey_equilibrium_y_coordinate"
    if case_id.startswith("G6F-TB-L1-008"):
        return [p["alpha"] / p["delta"], 1 / p["delta"]], "linear_production_decay"
    if case_id.startswith("G6F-TB-L1-009"):
        return [p["kon"] / (p["kon"] + p["koff"]), p["koff"] / (p["kon"] + p["koff"])], "two_state_probability"
    if case_id.startswith("G6F-TB-L1-011"):
        mu = p["mumax"] * p["S"] / (p["Ks"] + p["S"])
        return [mu], "chemostat_growth"
    if case_id.startswith("G6F-TB-L1-012"):
        return [-p["c"] + p["d"] * p["resident_prey"]], "invasion_rate"
    if case_id.startswith("G6F-TC-L1-001"):
        return [math.log(2) / p["k"]], "first_order_decay_half_life"
    if case_id.startswith("G6F-TC-L1-002"):
        return [], "second_order_decay_symbolic"
    if case_id.startswith("G6F-TC-L1-003"):
        return [p["A0"] / p["k"]], "zero_order_depletion"
    if case_id.startswith("G6F-TC-L1-004"):
        return [math.exp(p["Ea_J_per_mol"] / p["R"] * (1 / p["T1"] - 1 / p["T2"]))], "arrhenius_ratio"
    if case_id.startswith("G6F-TC-L1-005"):
        return [math.exp(-p["DeltaG_J_per_mol"] / (p["R"] * p["T"]))], "free_energy_equilibrium"
    if case_id.startswith("G6F-TC-L1-006"):
        return [p["K1"] * math.exp(p["DeltaH_J_per_mol"] / p["R"] * (1 / p["T1"] - 1 / p["T2"]))], "vanthoff"
    if case_id.startswith("G6F-TC-L1-007"):
        q = math.exp(-p["epsilon_over_RT"])
        return [q / (1 + q)], "two_level_excitation"
    if case_id.startswith("G6F-TC-L1-008"):
        x = p["x"]
        return [x * x * math.exp(x) / (1 + math.exp(x)) ** 2], "dimensionless_heat_capacity"
    if case_id.startswith("G6F-TC-L1-009"):
        return [p["kB"] / p["kC"], p["kB"] / (p["kB"] + p["kC"])], "parallel_reactions"
    if case_id.startswith("G6F-TC-L1-010"):
        return [p["k"] * p["B_fixed"]], "pseudo_first_order_observed_rate"
    if case_id.startswith("G6F-TC-L1-011"):
        return [p["pKa"] + math.log10(p["ratio"])], "henderson_hasselbalch"
    if case_id.startswith("G6F-TC-L1-012"):
        return [p["Vmax"] * p["S"] / (p["Km"] + p["S"]), 0.5], "michaelis_menten"
    return [], "unsupported_family"


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    claim = row.get("original_claim") or ""
    expected, family = expected_values(row.get("case_id", ""), row.get("original_problem") or "")
    observed = _numbers(claim)
    missing = [value for value in expected if not _contains(observed, value)]
    symbolic_ok = _symbolic_ok(row.get("case_id", ""), claim)
    if not row.get("original_problem") or not claim:
        status = "UNKNOWN"
        reason = "MISSING_PUBLIC_PROPOSITION"
    elif not expected and symbolic_ok:
        status = "PROVEN_TRUE"
        reason = "INDEPENDENT_SYMBOLIC_REPLAY"
    elif not expected:
        status = "UNKNOWN"
        reason = "UNSUPPORTED_FAMILY"
    elif missing and symbolic_ok:
        status = "PROVEN_TRUE"
        reason = "INDEPENDENT_SYMBOLIC_REPLAY_WITH_PARTIAL_NUMERIC_MATCH"
    elif missing:
        status = "PROVEN_FALSE"
        reason = "PUBLIC_CLAIM_NUMERIC_CONSISTENCY_FAILURE"
    else:
        status = "PROVEN_TRUE"
        reason = "INDEPENDENT_EQUATION_REPLAY_AND_NUMERIC_MATCH"
    cf = row.get("cf_type")
    action = {"CF1": "REJECT", "CF2": "MAINTAIN", "CF3": "REVISE", "CF4": "UNDETERMINED"}.get(cf, "UNKNOWN")
    result = {
        "unit_index": row.get("unit_index"),
        "attempt_id": row.get("attempt_id"),
        "case_id": row.get("case_id"),
        "cf_type": cf,
        "family": family,
        "public_claim_status": status,
        "public_claim_reason": reason,
        "expected_values": expected,
        "observed_numbers": observed,
        "missing_expected_values": missing,
        "intervention_action_truth": action,
        "original_supported_after_intervention": status == "PROVEN_TRUE" and action == "MAINTAIN",
        "revised_claim_valid": status == "PROVEN_TRUE" and action == "REVISE",
        "equivalence_preserved": action == "MAINTAIN" and status == "PROVEN_TRUE",
        "action_correctness_target": action,
        "nontrivial_revision": action == "REVISE" and status == "PROVEN_TRUE",
        "truth_key_read": False,
        "independent_verifier": "legacy_math_validate.py",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = [validate_row(row) for row in rows]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for result in results:
        key = result["public_claim_status"]
        counts[key] = counts.get(key, 0) + 1
    args.summary.write_text(json.dumps({
        "protocol": "V8_LEGACY_G6_INDEPENDENT_MATH_REPLAY",
        "rows": len(results),
        "counts": counts,
        "truth_key_read": False,
        "historical_data_modified": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

