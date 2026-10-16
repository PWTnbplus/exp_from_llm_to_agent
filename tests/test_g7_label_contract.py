from __future__ import annotations

from scripts.run_g7_failure_localization import protocol_preflight


def _public() -> list[dict]:
    return [{"case_id": "case-1", "model_visible": {"problem": "public"}}]


def _plan(stages: list[str]) -> list[dict]:
    return [{
        "run_id": "run-1",
        "checkpoint_id": "checkpoint-1",
        "case_id": "case-1",
        "group_id": "G4",
        "diagnostic_arm": "D2" if stages == ["V", "L"] else "D3",
        "inject_stages": stages,
    }]


def _label(*, nodes=None, edges=None, changes=None) -> list[dict]:
    return [{
        "case_id": "case-1",
        "v": {"verdict": "SUPPORTED"},
        "l": {"nodes": [] if nodes is None else nodes, "edges": [] if edges is None else edges},
        "u": {"node_changes": [] if changes is None else changes},
        "eligible_u": True,
        "verifier_ref": "private-ref",
    }]


def test_preflight_rejects_private_nested_label_payload_before_provider() -> None:
    report = protocol_preflight(
        _public(),
        _label(nodes=[{"ground_truth": "hidden"}]),
        _plan(["V", "L"]),
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert "invalid_label_contract" in report["errors"]


def test_preflight_rejects_extra_nested_label_fields() -> None:
    report = protocol_preflight(
        _public(),
        _label(edges=[{"from": "C1", "to": "C2", "answer_key": "hidden"}]),
        _plan(["V", "L"]),
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert "invalid_label_contract" in report["errors"]


def test_preflight_rejects_extra_node_change_fields() -> None:
    report = protocol_preflight(
        _public(),
        _label(changes=[{"claim_id": "C1", "to_status": "supported", "private_oracle": "hidden"}]),
        _plan(["V", "L", "U"]),
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert "invalid_label_contract" in report["errors"]


def test_preflight_accepts_strict_public_label_shape() -> None:
    report = protocol_preflight(
        _public(),
        _label(nodes=["C1"], edges=[{"from": "C1", "to": "C2"}],
               changes=[{"claim_id": "C2", "to_status": "uncertain"}]),
        _plan(["V", "L"]),
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is True
    assert report["errors"] == []


def test_preflight_scans_model_visible_diagnostic_payload_for_private_metadata() -> None:
    report = protocol_preflight(
        _public(),
        _label(nodes=["verifier_ref"]),
        _plan(["V", "L"]),
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert "private_oracle_metadata_in_model_prompt" in report["errors"]
    assert report["forbidden_model_prompt_hits"]["verifier_ref"] == 1


def test_preflight_retains_explicitly_ineligible_u_rows_without_claiming_diagnostic_eligibility() -> None:
    plan = _plan(["U"])
    plan[0]["diagnostic_arm"] = "U_ONLY"
    plan[0]["arm_eligible_for_diagnostic"] = False
    report = protocol_preflight(
        _public(),
        _label(),
        plan,
        worker_count=1,
        require_complete_plan=False,
    )
    assert report["formal_run_allowed_by_protocol"] is True
    assert "ineligible_u_diagnostic_arm" not in report["errors"]
    assert report["counts"]["ineligible_u_diagnostic_rows"] == []
