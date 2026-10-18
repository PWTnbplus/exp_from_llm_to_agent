from __future__ import annotations

import json
from pathlib import Path

from scripts.v3.build_public_lu_graphs import build_graph, proof_for
from scripts.v3.q_v2 import verify_q_record
from scripts.v3.run_q_v2_cohort import public_prompt


def test_public_lu_proof_and_graph_are_independently_validated() -> None:
    task = {
        "task_id": "TC-L1-001",
        "mathematical_model": "dA/dt=-kA",
        "assumptions": ["A0>0", "k>0"],
    }
    proof = proof_for(task)
    assert proof is not None and proof["proof_pass"] is True
    graph = build_graph(task, "proofs/TC-L1-001.json")
    from scripts.v3.lu_v2 import validate_public_dag
    assert validate_public_dag(graph)["acyclic"] is True
    assert graph["u_transition_eligible"] is False


def test_q_v2_record_uses_independent_local_verifier() -> None:
    candidate = {
        "claim_id": "public-claim",
        "claim_type": "monotonicity",
        "typed_ast": {"op": "mul", "args": [{"op": "number", "value": -1}, {"op": "variable", "name": "x"}]},
        "assumptions": ["x is real"],
        "quantifiers": ["forall x"],
        "domain": {"variable": "x"},
        "relation": "decreasing",
        "time_interval": None,
        "origin": "MODEL_GENERATED",
    }
    result = verify_q_record({
        "candidate": candidate,
        "q_evidence": {
            "checker_requested": True,
            "tool_call_ids": ["local-q-v2"],
            "verifier_input_hash": "x" * 64,
            "verifier_output_ref": "proof.json",
        },
        "final_decision": "REJECT",
    })
    assert result["status"] == "PASS"


def test_public_prompt_does_not_include_routing_fields() -> None:
    prompt = public_prompt({
        "case_id": "case-1",
        "model_visible": {
            "original_problem": "dA/dt=-kA",
            "intervention_statement": "change k",
            "original_claim": "claim",
            "public_proof_graph": {"nodes": [], "edges": []},
        },
    })
    assert "source_task_id" not in json.dumps(prompt)
    assert "expected_decision" not in json.dumps(prompt)
