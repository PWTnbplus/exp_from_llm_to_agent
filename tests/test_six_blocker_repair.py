from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_repair.math_verifier import verify_counterfactual
from scripts.audit_repair.verify_q import verify_state
from scripts.run_g7_failure_localization import emit
from scripts.audit_g7_trace_q_consistency import validate_lifecycle
from src.scientific_discovery.models.provider import OpenAICompatibleProvider


def test_math_verifier_counterfactual_positive_negative_quantifier_and_boundary() -> None:
    assert verify_counterfactual(cf_type="CF2", claim="variable renaming preserves the equation").status == "PASS"
    assert verify_counterfactual(cf_type="CF1", claim="with k<0 the direction reverses").status == "FAIL"
    assert verify_counterfactual(cf_type="CF3", claim="all k>=0 give strict decrease").status == "FAIL"
    assert verify_counterfactual(cf_type="CF3", claim="at k=0 strict decrease is not guaranteed").status == "PASS"
    assert verify_counterfactual(cf_type="CF4", claim="the sign is unknown, so the direction is undetermined").status == "PASS"
    assert verify_counterfactual(cf_type="CF4", claim="numeric samples on [0,1] look positive").status == "INCONCLUSIVE"
    assert verify_counterfactual(cf_type="CF3", claim="unrelated premise only").status == "INCONCLUSIVE"


def test_trace_writer_uses_explicit_request_and_tool_parents(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    seq = emit(path, 0, "run-1", "RUN_START", "RUNNING", {})
    seq = emit(path, seq, "run-1", "MODEL_REQUEST", "RUNNING", {})
    request_step = "run-1:step-000002"
    seq = emit(path, seq, "run-1", "MODEL_RESPONSE", "COMPLETED", {}, parent_step_id=request_step)
    seq = emit(path, seq, "run-1", "TOOL_CALL", "RUNNING", {})
    tool_step = "run-1:step-000004"
    seq = emit(path, seq, "run-1", "TOOL_RESULT", "COMPLETED", {}, parent_step_id=tool_step)
    seq = emit(path, seq, "run-1", "RUN_END", "COMPLETED", {"status": "completed"})
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert events[2]["parent_step_id"] == request_step
    assert events[4]["parent_step_id"] == tool_step
    assert all(event["attempt_id"] == path.parent.name for event in events)
    assert validate_lifecycle(events, {"run-1"}) == []


def test_q_verifier_does_not_accept_final_decision_or_oracle_as_evidence(tmp_path: Path) -> None:
    state = {
        "run_id": "s1", "status": "completed", "final_decision": "REVISE",
        "stages": {"Q": {"verdict": "PASS", "reason": "The final decision is correct."}},
    }
    plan = {"run_id": "s1", "case_id": "case-1", "cf_type": "CF3"}
    public = {"case_id": "case-1", "quantifier": "forall_allowed_parameters", "model_visible": {"original_problem": "dx/dt=-kx"}}
    result = verify_state(state, plan, public)
    assert result["status"] == "NOT_SCORED"
    assert result["actual_check_executed"] is False
    assert result["reason_code"] == "MODEL_Q_FREE_TEXT_NO_REPLAYABLE_CLAIM"


def test_paid_provider_refuses_network_without_atomic_cost_ledger() -> None:
    provider = OpenAICompatibleProvider(
        api_key="test-key", model_name="test-model", input_cost_per_1k=1.0,
        output_cost_per_1k=1.0, require_cost_ledger=True,
    )
    try:
        provider.complete([{"role": "user", "content": "hello"}])
    except RuntimeError as exc:
        assert "cost ledger" in str(exc)
    else:
        raise AssertionError("provider call unexpectedly passed without a ledger")
