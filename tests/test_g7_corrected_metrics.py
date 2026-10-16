from __future__ import annotations

from scripts.audit_g7_corrected_metrics import build_report


def _plan(run_id: str, arm: str, checkpoint: str = "cp-1") -> dict:
    return {"run_id": run_id, "case_id": "case-1", "group_id": "G4",
            "diagnostic_arm": arm, "checkpoint_id": checkpoint}


def test_corrected_metrics_keep_failed_rows_and_block_confirmatory_reuse() -> None:
    plan = [_plan("run-d0", "D0"), _plan("run-d1", "D1"), _plan("run-d2", "D2"),
            _plan("run-d3", "D3"), _plan("run-u", "U_ONLY"), _plan("run-v", "V_ONLY")]
    states = [
        {"run_id": "run-d0", "status": "completed", "initial_decision": "REJECT", "final_decision": "MAINTAIN"},
        {"run_id": "run-d1", "status": "completed", "initial_decision": "MAINTAIN", "final_decision": "REJECT"},
        {"run_id": "run-d2", "status": "provider_error"},
        {"run_id": "run-d3", "status": "completed", "initial_decision": "REJECT", "final_decision": "MAINTAIN"},
        {"run_id": "run-u", "status": "completed", "initial_decision": "REJECT", "final_decision": "MAINTAIN"},
        {"run_id": "run-v", "status": "completed", "initial_decision": "REJECT", "final_decision": "REJECT"},
    ]
    q = [
        {"run_id": "run-d0", "is_valid": True, "checks": {"V": True, "L": True, "U": True, "Q": True, "final_decision": True}},
        {"run_id": "run-d1", "is_valid": False, "checks": {"V": False, "L": True, "U": True, "Q": True, "final_decision": True}},
        {"run_id": "run-d2", "is_valid": False},
        {"run_id": "run-d3", "is_valid": True, "checks": {"V": True, "L": True, "U": True, "Q": True, "final_decision": True}},
        {"run_id": "run-u", "is_valid": True, "checks": {"V": True, "L": True, "U": True, "Q": True, "final_decision": True}},
        {"run_id": "run-v", "is_valid": True, "checks": {"V": True, "L": True, "U": True, "Q": True, "final_decision": True}},
    ]
    report = build_report(
        plan_rows=plan, state_rows=states, q_rows=q,
        oracle_rows=[{"case_id": "case-1", "expected_decision": "MAINTAIN"}],
        preflight={"errors": ["ineligible_u_diagnostic_arm"], "counts": {"ineligible_u_diagnostic_rows": ["run-d3", "run-u"]}},
        input_hashes={},
    )
    d0 = report["by_arm"]["G4__D0"]
    assert d0["planned"] == 1
    assert d0["all_planned_correct"] == 1
    assert d0["valid_only_accuracy"] == 1.0
    assert report["counts"]["terminal_failures"] == 1
    assert report["counts"]["invalid_q_rows"] == 2
    assert report["confirmatory_reuse_allowed"] is False
    assert report["paired_diagnostic_status"]["G4:U_ONLY_minus_D0"]["status"] == "NOT_COMPUTABLE_INELIGIBLE_U"
    def keys(value):
        if isinstance(value, dict):
            return set(value) | {key for child in value.values() for key in keys(child)}
        if isinstance(value, list):
            return {key for child in value for key in keys(child)}
        return set()
    assert "expected_decision" not in keys(report)
