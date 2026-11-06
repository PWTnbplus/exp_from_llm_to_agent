from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json
from scripts.v7.math_claim_ir import parse_claim
from scripts.v7.math_verify_sympy import verify


def generate(tasks: Path, out: Path, proof_dir: Path) -> dict[str, Any]:
    rows = read_jsonl(tasks); graphs = []; proof_rows = []; skipped = []
    proof_dir.mkdir(parents=True, exist_ok=True)
    for task in rows:
        try:
            control_ir = parse_claim(task["control_claim"].replace("^", "**"))
            intervention_ir = parse_claim(task["intervention_claim"].replace("^", "**"))
            control_verification = verify(control_ir); intervention_verification = verify(intervention_ir)
        except Exception as exc:
            skipped.append({"task_id": task.get("task_id"), "reason": type(exc).__name__}); continue
        proof = {"task_id": task["task_id"], "rule_id": "controlled_polynomial_derivative_v1", "control": control_verification, "intervention": intervention_verification, "public_truth_only": True, "answer_key_read": False}
        proof_path = proof_dir / f"{task['task_id']}.json"; write_json(proof_path, proof)
        graph = {
            "graph_id": "v7-public-lu:" + task["task_id"], "task_id": task["task_id"], "is_demo": False,
            "nodes": [
                {"claim_id": task["task_id"] + ":assumptions", "kind": "assumption", "statement": task["domain"]},
                {"claim_id": task["task_id"] + ":M", "kind": "nonfinal_intermediate_claim", "statement": task["control_claim"]},
                {"claim_id": task["task_id"] + ":Y", "kind": "final_claim", "statement": "separate final task outcome"},
            ],
            "edges": [
                {"from_claim_id": task["task_id"] + ":assumptions", "to_intermediate_claim_id": task["task_id"] + ":M", "rule_id": "public_claim_instantiation", "assumptions": [task["domain"]], "formal_obligation": "controlled_polynomial_parse", "proof_certificate_ref": str(proof_path).replace("\\", "/")},
                {"from_claim_id": task["task_id"] + ":M", "to_intermediate_claim_id": task["task_id"] + ":Y", "rule_id": "final_outcome_scored_separately", "assumptions": ["no reverse inference from Y to U"], "formal_obligation": "separate_observable_model_state", "proof_certificate_ref": str(proof_path).replace("\\", "/")},
            ],
            "u_transition_eligible": False, "u_transition_reason": "no immutable public checkpoint fork in reused historical calls",
            "proof_sha256": sha256_file(proof_path),
        }
        graphs.append(graph); proof_rows.append({"task_id": task["task_id"], "proof_ref": str(proof_path), "proof_sha256": graph["proof_sha256"], "control_result": control_verification["result"], "intervention_result": intervention_verification["result"]})
    write_jsonl(out, graphs)
    result = {"graph_count": len(graphs), "edge_count": sum(len(x["edges"]) for x in graphs), "proof_count": len(proof_rows), "skipped": skipped, "source_sha256": sha256_file(tasks), "truth_key_read": False, "u_transition_candidates": 0, "u_transition_verified": 0}
    write_json(out.with_name("LU_GRAPH_GENERATION_MANIFEST.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--tasks", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); parser.add_argument("--proof-dir", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(generate(args.tasks, args.out, args.proof_dir), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
