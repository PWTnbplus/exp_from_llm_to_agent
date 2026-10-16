"""Independent verifier for the 24 G5 families selected for G6.

This verifier reads only the public benchmark, the selected public G5 graph,
and its structural summary.  It never opens an answer key or G6 private
oracle.  The task-specific checks are analytic/numeric consequences of the
published model and parameters, not checks against the model's reported
answer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def index_unique(rows: Any, field: str, label: str) -> dict[str, dict[str, Any]]:
    """Index records only when identifiers are unique and well-formed."""
    if not isinstance(rows, list):
        raise SystemExit(f"{label} must be a JSON list")
    indexed: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SystemExit(f"{label} row {position} must be an object")
        value = row.get(field)
        if not isinstance(value, str) or not value:
            raise SystemExit(f"{label} row {position} has missing or invalid {field}")
        if value in indexed:
            raise SystemExit(f"duplicate {label} {field}: {value}")
        indexed[value] = row
    return indexed


def normalise(text: str) -> str:
    table = str.maketrans({
        "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
        "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
        "²": "2", "³": "3", "⁻": "-", "μ": "mu", "Δ": "delta",
        "ε": "epsilon", "β": "beta", "γ": "gamma", "δ": "delta", "α": "alpha",
        "θ": "theta", "τ": "tau", "∞": "infinity",
    })
    return re.sub(r"\s+", "", text.translate(table).casefold())


def numbers(text: str) -> list[float]:
    pattern = r"(?<![A-Za-z])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    return [float(item) for item in re.findall(pattern, text)]


def near_in_text(value: float, text: str, tolerance: float = 2e-4) -> bool:
    return any(abs(value - candidate) <= tolerance * max(1.0, abs(value)) for candidate in numbers(text))


def check_task(task_id: str, params: dict[str, Any]) -> tuple[list[float], list[list[str]], str | None]:
    """Return computed values, semantic token groups, and an exclusion reason."""
    p = {key: float(value) for key, value in params.items() if isinstance(value, (int, float))}
    if task_id == "TC-L1-001":
        return [math.log(2) / p["k"]], [["dA/dt"], ["exp"], ["A0"], ["ln(2)", "half"]], None
    if task_id == "TC-L1-002":
        return [1 / (p["k"] * p["A0"])], [["1/A"], ["A0"], ["k"], ["half"]], None
    if task_id == "TC-L1-003":
        return [p["A0"] / p["k"]], [["A(t)"], ["A0"], ["A0/k"], ["domain"]], None
    if task_id == "TC-L1-004":
        value = math.exp(p["Ea_J_per_mol"] / p["R"] * (1 / p["T1"] - 1 / p["T2"]))
        return [value], [["ratio"], ["exp"], ["Ea"], ["T1"]], None
    if task_id == "TC-L1-005":
        value = math.exp(-p["DeltaG_J_per_mol"] / (p["R"] * p["T"]))
        return [value], [["K"], ["exp"], ["deltaG", "dg"]], None
    if task_id == "TC-L1-006":
        value = p["K1"] * math.exp(p["DeltaH_J_per_mol"] / p["R"] * (1 / p["T1"] - 1 / p["T2"]))
        return [value], [["ln"], ["K2", "K"], ["deltaH", "dh"], ["T1"]], None
    if task_id == "TC-L1-007":
        z = 1 + math.exp(-p["epsilon_over_RT"])
        excited = math.exp(-p["epsilon_over_RT"]) / z
        return [z, excited], [["Z"], ["exp"], ["excited", "energy"]], None
    if task_id == "TC-L1-008":
        x = p["x"]
        value = x * x * math.exp(x) / (1 + math.exp(x)) ** 2
        return [value, 0.0], [["C_V/R", "CV/R", "heat"], ["x"], ["infinity", "limit"]], None
    if task_id == "TC-L1-009":
        return [p["kB"] / p["kC"], p["kB"] / (p["kB"] + p["kC"])], [["kB"], ["kC"], ["ratio"], ["fraction"]], None
    if task_id == "TC-L1-010":
        k_obs = p["k"] * p["B_fixed"]
        return [k_obs, math.log(2) / k_obs], [["k_obs", "kobs"], ["B"], ["half"]], None
    if task_id == "TC-L1-011":
        return [p["pKa"] + math.log10(p["ratio"])], [["pH"], ["log"], ["ratio"]], None
    if task_id == "TC-L1-012":
        return [p["Vmax"] * p["S"] / (p["Km"] + p["S"]), 0.5], [["Vmax"], ["Km"], ["S"], ["0.5", "half"]], None
    if task_id == "TB-L1-001":
        return [p["N0"] * math.exp(p["r"] * p["t"]), math.log(2) / p["r"]], [["dN/dt"], ["exp"], ["doubling"]], None
    if task_id == "TB-L1-002":
        return [p["K"]], [["logistic"], ["equilibrium"], ["stable"], ["unstable"]], None
    if task_id == "TB-L1-003":
        discriminant = p["K"] ** 2 - 4 * p["h"] * p["K"] / p["r"]
        low = (p["K"] - math.sqrt(discriminant)) / 2
        high = (p["K"] + math.sqrt(discriminant)) / 2
        return [low, high], [["quadratic"], ["root"], ["stable"], ["unstable"]], None
    if task_id == "TB-L1-004":
        return [p["beta"] / p["gamma"]], [["R0"], ["3.0", "beta"], ["unstable", "不稳定"]], None
    if task_id == "TB-L1-005":
        value = p["Vmax"] * p["S"] / (p["Km"] + p["S"] + p["S"] ** 2 / p["Ki"])
        return [value, 0.0], [["substrate"], ["inhibition"], ["S2", "S^2"], ["infinity", "limit"]], None
    if task_id == "TB-L1-006":
        return [p["S"] / (p["K"] + p["S"]), 0.5], [["theta"], ["S"], ["K"], ["half", "半饱和"]], None
    if task_id == "TB-L1-007":
        return [p["c"] / p["d"], p["a"] / p["b"]], [["dx/dt"], ["dy/dt"], ["x*"], ["y*"]], None
    if task_id == "TB-L1-008":
        return [p["alpha"] / p["delta"], 1 / p["delta"]], [["P*", "P"], ["tau"], ["alpha"], ["delta", "δ"]], None
    if task_id == "TB-L1-009":
        on = p["kon"] / (p["kon"] + p["koff"])
        return [on, 1 - on], [["p_on", "pon"], ["p_off", "poff"], ["denominator"]], None
    if task_id == "TB-L1-010":
        return [], [["q"]], "Excluded: the public task labels q*=mu/s as a recessive deleterious-allele balance, but the standard recessive mutation-selection balance is q≈sqrt(mu/s); the source graph also leaves this model-validity claim unresolved."
    if task_id == "TB-L1-011":
        mu = p["mumax"] * p["S"] / (p["Ks"] + p["S"])
        return [mu], [["mu(S)", "mu"], ["D"], ["grow", "growth", "可增长"]], None
    if task_id == "TB-L1-012":
        return [-p["c"] + p["d"] * p["resident_prey"]], [["invasion"], ["-c"], ["resident"]], None
    raise KeyError(task_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g6-out", type=Path, required=True)
    parser.add_argument("--public-tasks", type=Path, default=Path("data/theory_benchmark_v2/public_tasks.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    public = index_unique(read_json(args.public_tasks), "task_id", "public task")
    index = read_json(args.g6_out / "G6_SOURCE_INDEX.json")
    source_rows = index_unique(index.get("source_rows"), "task_id", "G6 source index")
    rows: list[dict[str, Any]] = []
    for source in source_rows.values():
        task_id = source["task_id"]
        task = public.get(task_id)
        failures: list[str] = []
        if task is None:
            failures.append("public_task_missing")
            rows.append({"task_id": task_id, "status": "UNVERIFIED", "failures": failures})
            continue
        graph_path = Path(source["graph_path"])
        if not graph_path.is_file():
            failures.append("graph_missing")
            rows.append({"task_id": task_id, "status": "UNVERIFIED", "failures": failures})
            continue
        if sha256(graph_path) != source.get("graph_sha256"):
            failures.append("graph_hash_mismatch")
        graph = read_json(graph_path)
        summary_path = graph_path.parent / "summary.json"
        summary = read_json(summary_path) if summary_path.is_file() else {}
        if summary.get("status") != "COMPLETED" or summary.get("final_validation", {}).get("status") != "PASS":
            failures.append("g5_structural_summary_not_completed")
        nodes = graph.get("nodes") if isinstance(graph, dict) else None
        if not isinstance(nodes, list) or not nodes:
            failures.append("nodes_missing")
            nodes = []
        try:
            expected_values, token_groups, exclusion = check_task(task_id, task.get("given_parameters", {}))
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            expected_values, token_groups, exclusion = [], [], f"independent_check_error:{type(exc).__name__}"
        text = " ".join(str(node.get("statement", "")) for node in nodes)
        normal = normalise(text)
        if exclusion:
            status = "EXCLUDED_INVALID_SOURCE"
            failures.append(exclusion)
        else:
            if any(node.get("status") != "supported" for node in nodes):
                failures.append("unsupported_or_unresolved_graph_node")
            if any(not node.get("evidence_refs") for node in nodes):
                failures.append("missing_graph_evidence_ref")
            for group in token_groups:
                if not any(normalise(token) in normal for token in group):
                    failures.append("missing_semantic_token:" + "/".join(group))
            for value in expected_values:
                if not near_in_text(value, text):
                    failures.append(f"numeric_claim_not_found:{value:.12g}")
            status = "VERIFIED_INDEPENDENT_B" if not failures else "UNVERIFIED"
        rows.append({
            "task_id": task_id,
            "status": status,
            "verification_grade": "B" if status == "VERIFIED_INDEPENDENT_B" else None,
            "source_graph_sha256": source.get("graph_sha256"),
            "computed_values": expected_values,
            "checked_node_count": len(nodes),
            "failures": failures,
            "method": "public-model analytic/numeric verification; no answer_key or private_oracle read",
        })
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    report = {
        "verifier": "g5_g6_public_model_independent_verifier_v1",
        "source": "public_tasks.json + G6_SOURCE_INDEX selected proof_graph/summary files",
        "private_inputs_read": False,
        "answer_key_read": False,
        "family_count": len(rows),
        "status_counts": counts,
        "verified_family_ids": [row["task_id"] for row in rows if row["status"] == "VERIFIED_INDEPENDENT_B"],
        "excluded_family_ids": [row["task_id"] for row in rows if row["status"] == "EXCLUDED_INVALID_SOURCE"],
        "rows": rows,
        "release_rule": "Only VERIFIED_INDEPENDENT_B families may enter the corrected formal G6 release; EXCLUDED_INVALID_SOURCE is never padded or relabeled.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["verifier", "family_count", "status_counts", "verified_family_ids", "excluded_family_ids", "private_inputs_read", "answer_key_read"]}, ensure_ascii=False))
    return 0 if counts.get("UNVERIFIED", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
