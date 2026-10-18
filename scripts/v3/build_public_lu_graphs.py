"""Build auditable L dependency graphs from public math tasks only.

Only two public ODE families with short symbolic proofs are enabled.  The
builder never reads an answer key or private G7 labels.  It records U as
ineligible unless an observed model-state transition exists; a mathematical
derivation is not silently relabeled as model behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import sympy as sp

try:
    from scripts.v3.lu_v2 import graph_sha256, validate_public_dag
except ModuleNotFoundError:  # direct ``python scripts/v3/build_public_lu_graphs.py``
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.v3.lu_v2 import graph_sha256, validate_public_dag


RULES = {
    "dA/dt=-kA": "exponential_decay_solution",
    "dA/dt=-kA^2": "reciprocal_decay_solution",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError("public task file must contain an array of objects")
    return value


def proof_for(task: dict[str, Any]) -> dict[str, Any] | None:
    model = str(task.get("mathematical_model", "")).split(" ", 1)[0]
    if model == "dA/dt=-kA":
        A0, k, t, A = sp.symbols("A0 k t A", real=True)
        expression = A0 * sp.exp(-k * t)
        residual = sp.simplify(sp.diff(expression, t) + k * expression)
        checks = {"ode_residual_zero": residual == 0, "initial_value": sp.simplify(expression.subs(t, 0) - A0) == 0}
        derivation = "A(t)=A0*exp(-k*t); substitute into dA/dt+kA=0 and verify A(0)=A0."
    elif model == "dA/dt=-kA^2":
        A0, k, t, A = sp.symbols("A0 k t A", real=True)
        reciprocal = 1 / A0 + k * t
        checks = {"reciprocal_derivative_k": sp.simplify(sp.diff(reciprocal, t) - k) == 0,
                  "initial_reciprocal": sp.simplify(reciprocal.subs(t, 0) - 1 / A0) == 0}
        derivation = "Differentiate 1/A: d(1/A)/dt=-(1/A^2)dA/dt=k, then integrate from 0 to t."
    else:
        return None
    return {
        "proof_type": "sympy_independent_public_derivation",
        "task_id": task["task_id"],
        "public_model": task["mathematical_model"],
        "derivation": derivation,
        "symbolic_checks": checks,
        "proof_pass": all(checks.values()),
        "answer_key_read": False,
    }


def build_graph(task: dict[str, Any], proof_ref: str) -> dict[str, Any]:
    task_id = str(task["task_id"])
    model = str(task["mathematical_model"])
    graph = {
        "protocol_id": "LU_V2_PUBLIC_DERIVED",
        "graph_id": f"public-lu-v2:{task_id}",
        "source": "PUBLIC_MATHEMATICAL_TASK",
        "nodes": [
            {"claim_id": f"{task_id}:assumptions", "kind": "assumption", "statement": "public task assumptions"},
            {"claim_id": f"{task_id}:model", "kind": "intermediate", "statement": model},
            {"claim_id": f"{task_id}:derived", "kind": "conclusion", "statement": "symbolically derived public consequence"},
        ],
        "edges": [],
        "u_transition_eligible": False,
        "u_transition_reason": "No observed model state was supplied; public derivation is not relabeled as OBSERVED_MODEL_STATE.",
    }
    graph["edges"] = [
        {
            "source_claim_id": f"{task_id}:assumptions",
            "target_claim_id": f"{task_id}:model",
            "inference_rule": "public_task_model_instantiation",
            "assumptions": list(task.get("assumptions", [])),
            "independent_proof_ref": proof_ref,
            "graph_sha256": "",
        },
        {
            "source_claim_id": f"{task_id}:model",
            "target_claim_id": f"{task_id}:derived",
            "inference_rule": RULES[model],
            "assumptions": ["public model only", "symbolic proof_pass=true"],
            "independent_proof_ref": proof_ref,
            "graph_sha256": "",
        },
    ]
    digest = graph_sha256(graph)
    for edge in graph["edges"]:
        edge["graph_sha256"] = digest
    return graph


def build(args: argparse.Namespace) -> dict[str, Any]:
    tasks = read_json(args.public)
    wanted = set(args.task_id or [])
    selected = [row for row in tasks if not wanted or row.get("task_id") in wanted]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.proof_dir.mkdir(parents=True, exist_ok=True)
    graphs: list[dict[str, Any]] = []
    proof_rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    for task in selected:
        proof = proof_for(task)
        if proof is None:
            skipped.append(str(task.get("task_id")))
            continue
        proof_path = args.proof_dir / f"{task['task_id']}.json"
        proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        proof_ref = str(proof_path.relative_to(args.out.parent)).replace("\\", "/")
        graph = build_graph(task, proof_ref)
        validation = validate_public_dag(graph)
        graphs.append(graph)
        proof_rows.append({"task_id": task["task_id"], "proof_ref": proof_ref, "proof_sha256": sha256_file(proof_path), "proof_pass": proof["proof_pass"], "graph_validation": validation})
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        for graph in graphs:
            handle.write(json.dumps(graph, ensure_ascii=False, separators=(",", ":")) + "\n")
    manifest = {
        "protocol_id": "LU_V2_PUBLIC_DERIVED",
        "public_input": str(args.public),
        "public_sha256": sha256_file(args.public),
        "graph_count": len(graphs),
        "edge_count": sum(len(graph["edges"]) for graph in graphs),
        "independently_verified_edges": sum(row["graph_validation"]["edge_count"] for row in proof_rows if row["graph_validation"]["acyclic"]),
        "u_transition_candidates": 0,
        "u_transition_verified": 0,
        "skipped_task_ids": skipped,
        "private_labels_read": False,
        "answer_key_read": False,
        "scientific_status": "PUBLIC_DERIVATION_ONLY_NOT_A_MODEL_BEHAVIOR_RESULT",
        "proofs": proof_rows,
    }
    manifest_path = args.manifest or args.out.with_name(args.out.stem + "_MANIFEST.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--proof-dir", type=Path, required=True)
    parser.add_argument("--task-id", action="append")
    args = parser.parse_args()
    try:
        result = build(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["graph_count"] > 0 and result["edge_count"] == result["independently_verified_edges"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
