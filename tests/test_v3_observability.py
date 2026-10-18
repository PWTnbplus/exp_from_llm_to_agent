from __future__ import annotations

import json

from scripts.v3.lu_v2 import graph_sha256, validate_nonfinal_transition, validate_public_dag
from scripts.v3.observability_smoke import fixture, run_smoke
from scripts.v3.q_v2 import verify_q_record


def test_v2_observability_smoke_and_anticheat(tmp_path):
    result = run_smoke(tmp_path / "smoke.json")
    assert result["status"] == "SMOKE_PASS"
    assert result["scientific_status"] == "SYNTHETIC_MOCK_NOT_SCIENTIFIC"
    assert all(result["anti_cheat"].values())


def test_q_v2_does_not_trust_final_decision_or_private_field():
    _, record, _ = fixture()
    altered = json.loads(json.dumps(record))
    altered["final_decision"] = "REJECT"
    assert verify_q_record(altered) == verify_q_record(record)
    leaked = json.loads(json.dumps(record))
    leaked["candidate"]["expected_decision"] = "PASS"
    assert verify_q_record(leaked)["status"] == "NOT_SCORED"


def test_lu_v2_rejects_cycles_and_final_only_updates():
    graph, _, transition = fixture()
    cyclic = json.loads(json.dumps(graph))
    cyclic["edges"].append({
        "source_claim_id": "M1", "target_claim_id": "A0", "inference_rule": "cycle",
        "assumptions": [], "independent_proof_ref": "synthetic://cycle", "graph_sha256": "",
    })
    cycle_hash = graph_sha256(cyclic)
    for edge in cyclic["edges"]: edge["graph_sha256"] = cycle_hash
    try:
        validate_public_dag(cyclic)
    except ValueError as exc:
        assert "cycle" in str(exc)
    else:
        raise AssertionError("cycle was accepted")
    final_only = dict(transition, claim_id="C1")
    final_only["state_before"] = {"status": "supported"}
    final_only["state_after"] = {"status": "refuted"}
    try:
        validate_nonfinal_transition(graph, final_only)
    except ValueError as exc:
        assert "final node" in str(exc)
    else:
        raise AssertionError("final-only U transition was accepted")
