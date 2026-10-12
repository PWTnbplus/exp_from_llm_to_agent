from __future__ import annotations

from scripts.audit_recover_failed_matrix_records import error_only, failure_class


def test_runner_exception_payload_is_not_an_answer() -> None:
    assert error_only({"error": "RuntimeError: provider failed"})
    assert not error_only({"final_answer": {"value": 1}, "derivation": "x"})


def test_failed_provider_is_not_classified_as_wrong() -> None:
    result = {
        "status": "FAILED",
        "answer": {"error": "RuntimeError: provider request failed"},
        "validation": {"status": "MODEL_ERROR", "answer_correct": False, "errors": ["RuntimeError"]},
        "metadata": {"provider_trace": [{"error": {"type": "HTTPError", "message": "HTTP Error 403"}}]},
    }
    assert failure_class(result, has_response=False) == "FAILED_PROVIDER_ACCESS"


def test_completed_real_mismatch_is_wrong() -> None:
    result = {
        "status": "COMPLETED",
        "answer": {"final_answer": {"value": 2}},
        "validation": {"status": "MODEL_ERROR", "answer_correct": False, "errors": ["validation mismatch"]},
        "metadata": {"provider_trace": []},
    }
    assert failure_class(result, has_response=False) == "ANSWER_WRONG"
