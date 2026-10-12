from __future__ import annotations

from scripts.audit_exhaustive_local_recovery import classify_evaluations, recovery_key, response_candidates


def test_failed_payload_pass_is_a_recovery_diagnostic() -> None:
    assert classify_evaluations(["MODEL_ERROR", "PASS"]) == "FAILED_RECOVERED_CORRECT"


def test_failed_payload_mismatch_is_not_wrong() -> None:
    assert classify_evaluations(["MODEL_ERROR"]) == "FAILED_WITH_PERSISTED_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED"


def test_recovery_key_is_stable_and_excludes_candidate_content() -> None:
    row = {"group": "G4", "run_dir": "run", "model_id": "m", "task_id": "TB-L1-001", "candidate_sha256": "secret-content-hash"}
    assert recovery_key(row) == ("G4", "run", "m", "TB-L1-001")


def test_persisted_trace_with_trailing_comma_is_recoverable_without_a_provider_call() -> None:
    result = {
        "answer": {"error": "JSONDecodeError"},
        "metadata": {
            "provider_trace": [
                {"call_index": 0, "response": {"content": '{"task_id":"TB-L1-001","final_answer":{"value":1,},}'}}
            ]
        },
    }
    candidates = response_candidates(result)
    assert candidates
    assert candidates[0][2]["task_id"] == "TB-L1-001"
