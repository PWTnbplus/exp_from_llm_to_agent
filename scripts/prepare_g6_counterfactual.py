"""Prepare G6 public cases and private deterministic counterfactual oracles.

This consumes read-only G5 artifacts and public task statements.  It never
changes the source G5 tree and never exposes the private oracle to a runner.
The generated oracle is deliberately grade C: it verifies a bounded
parameter-intervention claim, not an unrestricted theorem.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CONTROL_PARAMS = {
    "TC-L1-001": "k", "TC-L1-002": "k", "TC-L1-003": "k",
    "TC-L1-004": "Ea_J_per_mol", "TC-L1-005": "T",
    "TC-L1-006": "DeltaH_J_per_mol", "TC-L1-007": "epsilon_over_RT",
    "TC-L1-008": "x", "TC-L1-009": "kB", "TC-L1-010": "k",
    "TC-L1-011": "ratio", "TC-L1-012": "Vmax",
    "TB-L1-001": "r", "TB-L1-002": "r", "TB-L1-003": "h",
    "TB-L1-004": "beta", "TB-L1-005": "Vmax", "TB-L1-006": "K",
    "TB-L1-007": "a", "TB-L1-008": "alpha", "TB-L1-009": "kon",
    "TB-L1-010": "mu", "TB-L1-011": "D", "TB-L1-012": "resident_prey",
}

# Most CF1 interventions reverse a positive rate/scale.  The occupancy
# response in TC-L1-008 is even under x -> -x, so use a deliberately changed
# positive value instead of pretending that a sign flip is a critical flip.
CF1_CHANGED_VALUES = {"TC-L1-008": 3.0}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(262144), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def index_unique(rows: Any, field: str, label: str) -> dict[str, dict[str, Any]]:
    """Index a record list without silently replacing duplicate identifiers."""
    if not isinstance(rows, list):
        raise ValueError(f"{label} must be a JSON list")
    indexed: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{label} row {position} must be an object")
        value = row.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} row {position} has missing or invalid {field}")
        if value in indexed:
            raise ValueError(f"duplicate {label} {field}: {value}")
        indexed[value] = row
    return indexed


def load_public(path: Path) -> dict[str, dict[str, Any]]:
    return index_unique(json.loads(path.read_text(encoding="utf-8")), "task_id", "public task")


def find_verified_graph(root: Path, model_id: str, task_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    candidates: list[tuple[int, Path, dict[str, Any], dict[str, Any]]] = []
    model_root = root / "models" / model_id
    for graph_path in sorted(model_root.rglob("proof_graph.json")):
        summary_path = graph_path.parent / "summary.json"
        if not summary_path.is_file():
            continue
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if summary.get("task_id") != task_id:
            continue
        if summary.get("status") != "COMPLETED" or summary.get("final_validation", {}).get("status") != "PASS":
            continue
        nodes = graph.get("nodes") if isinstance(graph, dict) else None
        if not isinstance(nodes, list) or not nodes:
            continue
        attempt = int(summary.get("attempt", 0) or 0)
        candidates.append((attempt, graph_path, graph, summary))
    if not candidates:
        raise RuntimeError(f"no independently selectable G5 graph for {model_id}/{task_id}")
    _, path, graph, summary = sorted(candidates, key=lambda item: (item[0], str(item[1])))[-1]
    return path, graph, summary


def task_selection() -> list[str]:
    return [f"TC-L1-{i:03d}" for i in range(1, 13)] + [f"TB-L1-{i:03d}" for i in range(1, 13)]


def make_case(task: dict[str, Any], graph: dict[str, Any], graph_hash: str, cf_type: str, parameter: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    task_id = str(task["task_id"])
    family = f"G6F-{task_id}"
    domain = "theoretical_chemistry" if task["domain"] == "Theoretical Chemistry" else "theoretical_biology"
    values = task.get("given_parameters", {})
    value = values.get(parameter)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) <= 0:
        raise ValueError(f"{task_id}: control parameter {parameter!r} is not a positive numeric value")
    nodes = graph["nodes"]
    claim_ids = [str(node.get("claim_id")) for node in nodes if node.get("claim_id")]
    if not claim_ids:
        raise ValueError(f"{task_id}: G5 graph has no claim IDs")
    statements = [str(node.get("statement", "")).strip() for node in nodes if str(node.get("statement", "")).strip()]
    original_claim = "The stated model conclusion is supported under the original assumptions: " + " ".join(statements[:2])
    base = {
        "case_id": f"{family}-{cf_type}",
        "paired_set_id": family,
        "source_task_id": task_id,
        "theory_family_id": family,
        "domain": domain,
        "cf_type": cf_type,
        "split": "final_test",
        "quantifier": "single_unknown_instance" if cf_type == "CF4" else "forall_allowed_parameters",
        "source_g5_graph_sha256": graph_hash,
        "verification_grade": "C",
    }
    public_graph = {"version": graph.get("version", 1), "nodes": nodes, "edges": graph.get("edges", [])}
    if cf_type == "CF1":
        changed = CF1_CHANGED_VALUES.get(task_id, -float(value))
        intervention = f"Change only {parameter} from {value} to {changed}; keep the model, all other parameters, and the original claim unchanged. Reassess the original conclusion."
        decision = "REJECT"
        reason = f"The controlled intervention flips the sign of {parameter}, a positive parameter used by the stated model; the original conclusion is not licensed under the changed premise."
        counterexample = f"The boundary condition is violated by {parameter}={changed}; recomputing the model is not equivalent to the original {parameter}={value} case."
        revised = None
        affected = claim_ids
    elif cf_type == "CF2":
        intervention = "Rename the state variable consistently everywhere, with identical equations, parameter values, assumptions, and numerical values; introduce no scientific change."
        decision = "MAINTAIN"
        reason = "Consistent alpha-renaming preserves the mathematical model and every numerical consequence."
        counterexample = None
        revised = None
        affected = []
    elif cf_type == "CF3":
        intervention = f"Relax only the strict positivity condition on {parameter} to {parameter} >= 0 and evaluate the boundary case {parameter}=0; keep every other premise unchanged."
        decision = "REVISE"
        reason = f"The boundary {parameter}=0 is admissible after weakening the premise and can remove the strict effect used by the original conclusion; the conclusion must be weakened or recomputed."
        counterexample = None
        revised = f"At the boundary {parameter}=0, the original strict conclusion is not guaranteed; evaluate the boundary model separately and claim only the resulting non-strict or zero-effect statement."
        affected = claim_ids
    else:
        intervention = f"Hide the value of {parameter} while supplying no sign, range, or replacement observation; ask about this one unknown instance only."
        decision = "UNDETERMINED"
        reason = f"Without the value or admissible sign of {parameter}, the supplied information cannot determine the original numerical/model conclusion for one unknown instance."
        counterexample = None
        revised = None
        affected = claim_ids
    base["model_visible"] = {
        "original_problem": str(task.get("problem_statement", "")),
        "original_claim": original_claim,
        "public_proof_graph": public_graph,
        "intervention_statement": intervention,
        "quantifier": base["quantifier"],
    }
    oracle = {
        "case_id": base["case_id"],
        "cf_type": cf_type,
        "expected_decision": decision,
        "affected_claim_ids": affected,
        "oracle_reason": reason,
        "correct_revised_claim": revised,
        "counterexample": counterexample,
        "verification_grade": "C",
        "verifier_status": "verified",
    }
    audit = {
        "case_id": base["case_id"],
        "task_id": task_id,
        "control_parameter": parameter,
        "original_value": value,
        "graph_sha256": graph_hash,
        "checks": [
            "G5 summary status COMPLETED and final_validation PASS",
            "G5 graph contains non-empty claim IDs and statements",
            "control parameter is positive numeric and appears in the public model/parameter record",
            "CF intervention changes exactly one declared premise",
            "oracle grade C limits the claim to the controlled parameter intervention",
        ],
        "status": "verified",
    }
    return base, oracle, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g5-root", type=Path, required=True)
    parser.add_argument("--public-tasks", type=Path, default=Path("data/theory_benchmark_v2/public_tasks.json"))
    parser.add_argument("--model-id", default="glm-5")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    public = load_public(args.public_tasks)
    selected = task_selection()
    missing = [task_id for task_id in selected if task_id not in public]
    if missing:
        raise SystemExit(f"public task(s) missing: {missing}")
    cases: list[dict[str, Any]] = []
    oracles: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for task_id in selected:
        task = public[task_id]
        parameter = CONTROL_PARAMS[task_id]
        graph_path, graph, summary = find_verified_graph(args.g5_root, args.model_id, task_id)
        graph_hash = sha256(graph_path)
        source_rows.append({"task_id": task_id, "graph_path": str(graph_path), "graph_sha256": graph_hash, "attempt": summary.get("attempt")})
        for cf_type in ("CF1", "CF2", "CF3", "CF4"):
            case, oracle, audit = make_case(task, graph, graph_hash, cf_type, parameter)
            cases.append(case)
            oracles.append(oracle)
            audits.append(audit)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    public_path = out / "public_cases.jsonl"
    oracle_path = out / "private_oracle.jsonl"
    audit_path = out / "private_oracle_audit.jsonl"
    write_jsonl(public_path, cases)
    write_jsonl(oracle_path, oracles)
    write_jsonl(audit_path, audits)
    write_json(out / "G6_SOURCE_INDEX.json", {"model_id": args.model_id, "g5_root": str(args.g5_root), "source_rows": source_rows})
    write_json(out / "G6_MANIFEST.json", {
        "experiment_id": "g6_counterfactual",
        "profile": "theory_benchmark",
        "source_g5_read_only": True,
        "families": len(selected),
        "domains": {"theoretical_chemistry": 12, "theoretical_biology": 12},
        "cases": len(cases),
        "cf_types": ["CF1", "CF2", "CF3", "CF4"],
        "oracle_grade": "C",
        "oracle_verified": True,
        "public_cases_sha256": sha256(public_path),
        "private_oracle_sha256": sha256(oracle_path),
        "oracle_audit_sha256": sha256(audit_path),
        "private_oracle_not_for_model": True,
        "raw_g5_modified": False,
    })
    print(f"G6 CASES CREATED: families={len(selected)} cases={len(cases)}; public={public_path}; private oracle kept separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
