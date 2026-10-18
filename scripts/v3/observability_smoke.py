"""Offline Q-v2/LU-v2 protocol smoke and anti-leakage tests.

The generated records are explicitly synthetic and are never counted as
scientific V2 results.  This command validates that a future real provider
run can be scored without altering legacy G7 rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.v3.lu_v2 import graph_sha256, validate_nonfinal_transition, validate_public_dag
from scripts.v3.q_v2 import verify_candidate, verify_q_record


def fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    graph = {
        "graph_id": "SYNTHETIC_LU_V2_001",
        "nodes": [
            {"claim_id": "A0", "kind": "assumption"},
            {"claim_id": "M1", "kind": "intermediate"},
            {"claim_id": "C1", "kind": "conclusion"},
        ],
        "edges": [],
    }
    graph_hash = graph_sha256(graph)
    graph["edges"] = [{
        "source_claim_id": "A0", "target_claim_id": "M1", "inference_rule": "synthetic_rule",
        "assumptions": ["x>0"], "independent_proof_ref": "synthetic://proof/A0-M1",
        "graph_sha256": "",
    }, {
        "source_claim_id": "M1", "target_claim_id": "C1", "inference_rule": "synthetic_rule",
        "assumptions": ["x>0"], "independent_proof_ref": "synthetic://proof/M1-C1",
        "graph_sha256": "",
    }]
    graph_hash = graph_sha256(graph)
    for edge in graph["edges"]: edge["graph_sha256"] = graph_hash
    candidate = {
        "claim_id": "M1", "claim_type": "monotonicity",
        "typed_ast": {"op": "mul", "args": [{"op": "number", "value": -1}, {"op": "variable", "name": "x"}]},
        "assumptions": ["x>0"], "quantifiers": ["forall x"], "domain": {"variable": "x", "lower": 0, "strict_lower": True},
        "relation": "decreasing", "time_interval": None, "origin": "MODEL_GENERATED",
    }
    q_record = {
        "protocol_id": "G7_Q_V2", "candidate": candidate,
        "q_evidence": {"checker_requested": True, "tool_call_ids": ["tool-q-v2-1"],
                       "verifier_input_hash": "i" * 64, "verifier_output_ref": "proofs/q-v2-1.json"},
        "final_decision": "MAINTAIN",
    }
    transition = {
        "state_before": {"status": "unresolved"}, "state_after": {"status": "supported"},
        "claim_id": "M1", "to_status": "supported", "trace_ref": "synthetic://trace/1",
        "source": "OBSERVED_MODEL_STATE",
    }
    return graph, q_record, transition


def run_smoke(out: Path) -> dict[str, Any]:
    graph, q_record, transition = fixture()
    graph_result = validate_public_dag(graph)
    transition_result = validate_nonfinal_transition(graph, transition)
    q_result = verify_q_record(q_record)
    # Four anti-cheat checks required by V3.
    q_claim = dict(q_record)
    q_claim["final_decision"] = "REJECT"
    final_decision_invariant = verify_q_record(q_claim) == q_result
    altered = json.loads(json.dumps(q_record))
    altered["candidate"]["typed_ast"]["args"][0]["value"] = 1
    altered_result = verify_q_record(altered)
    altered_claim_rejected = altered_result["status"] in {"FAIL", "INCONCLUSIVE", "NOT_SCORED"}
    unobserved = json.loads(json.dumps(q_record)); unobserved["q_evidence"]["tool_call_ids"] = []
    unobserved_result = verify_q_record(unobserved)
    private_injected = json.loads(json.dumps(q_record)); private_injected["candidate"]["expected_decision"] = "PASS"
    private_rejected = verify_q_record(private_injected)["status"] == "NOT_SCORED"
    result = {
        "protocol_id": "G7_Q_V2_AND_LU_V2",
        "status": "SMOKE_PASS" if all((graph_result["acyclic"], transition_result["eligible"], q_result["status"] == "PASS", final_decision_invariant, altered_claim_rejected, unobserved_result["reason_code"] == "UNOBSERVED_TOOL", private_rejected)) else "SMOKE_FAIL",
        "scientific_status": "SYNTHETIC_MOCK_NOT_SCIENTIFIC",
        "q": q_result, "lu_graph": graph_result, "lu_transition": transition_result,
        "anti_cheat": {
            "final_decision_invariant": final_decision_invariant,
            "altered_symbol_rejected": altered_claim_rejected,
            "unobserved_tool_rejected": unobserved_result["reason_code"] == "UNOBSERVED_TOOL",
            "private_field_rejected": private_rejected,
        },
        "real_v2_formal_runs": 0,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run_smoke(args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SMOKE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
