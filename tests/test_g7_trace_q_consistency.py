from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_g7_trace_q_consistency import (
    audit_trace_reference,
    build_report,
    classify_recorded_failure,
    validate_lifecycle,
)


def _write_events(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = []
    for index, event in enumerate(events, 1):
        value = dict(event)
        value.setdefault("seq", index)
        normalized.append(value)
    path.write_text("".join(json.dumps(event) + "\n" for event in normalized), encoding="utf-8")


def test_completed_q_requires_completed_error_free_trace(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "ERROR", "payload": {"error": "missing stage Q"}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "failed"}},
        ],
    )
    report = build_report(
        states=[state],
        q_rows=[{"run_id": "run-1", "is_valid": True}],
        trace_root=tmp_path,
    )
    review = report["states"]["reviews"][0]
    assert review["trace_ok"] is False
    assert review["trace_status"] == "trace_inconsistent"
    assert report["q"]["original_independent_valid"] == 1
    assert report["q"]["trace_backed_valid"] == 0
    assert report["q"]["valid_rows_invalidated_by_trace_review"] == 1
    assert report["conclusion"]["confirmatory_reuse_allowed"] is False
    assert report["states"]["recorded_failure_category_counts"]["response_contract_failure"] == 1


def test_latest_completed_segment_is_used_for_append_only_history(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "ERROR", "payload": {"error": "no valid JSON response"}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "provider_error"}},
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_REQUEST", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    review = audit_trace_reference(tmp_path, state)
    assert review["trace_ok"] is True
    assert review["trace_status"] == "pass"
    assert review["history_segment_count"] == 2


def test_terminal_provider_error_is_required_to_have_failure_evidence(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "provider_error", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "ERROR", "payload": {"error": "no valid JSON response"}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "provider_error"}},
        ],
    )
    review = audit_trace_reference(tmp_path, state)
    assert review["trace_status"] == "terminal_failure_evidence"
    assert review["failure_category"] == "response_contract_failure"
    assert review["trace_ok"] is True


def test_checkpoint_missing_without_trace_remains_explicit_not_executed(tmp_path: Path) -> None:
    review = audit_trace_reference(
        tmp_path,
        {"run_id": "run-1", "status": "checkpoint_missing", "trace_ref": None},
    )
    assert review["trace_status"] == "not_executed"
    assert review["trace_ok"] is True


def test_trace_path_escape_is_rejected_and_failure_categories_are_conservative(tmp_path: Path) -> None:
    review = audit_trace_reference(
        tmp_path,
        {"run_id": "run-1", "status": "completed", "trace_ref": "../outside/events.jsonl"},
    )
    assert review["trace_status"] == "trace_path_outside_root"
    assert classify_recorded_failure(["provider request failed after retries: timeout"]) == "transport_or_provider_failure"


def test_duplicate_lifecycle_events_are_not_hidden_by_segment_selection(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_REQUEST", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    review = audit_trace_reference(tmp_path, state)
    assert review["trace_ok"] is False
    assert "run_end_count:2" in review["lifecycle_reasons"]
    assert "run_end_count:2" in review["reasons"]


def test_duplicate_run_start_is_rejected_as_one_malformed_segment() -> None:
    events = [
        {"run_id": "run-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_type": "RUN_START", "seq": 2, "payload": {}},
        {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "seq": 3, "payload": {}},
        {"run_id": "run-1", "event_type": "RUN_END", "seq": 4, "payload": {"status": "completed"}},
    ]
    reasons = validate_lifecycle(events, {"run-1"})
    assert "run_start_count:2" in reasons
    assert "orphan_model_response" in reasons


def test_nonmonotonic_and_duplicate_sequences_invalidate_completed_trace(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_REQUEST", "seq": 3, "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "seq": 3, "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "seq": 4, "payload": {"status": "completed"}},
        ],
    )
    review = audit_trace_reference(tmp_path, state)
    assert review["trace_ok"] is False
    assert "duplicate_sequence" in review["lifecycle_reasons"]
    assert "sequence_not_strictly_increasing" in review["lifecycle_reasons"]


def test_duplicate_event_ids_are_reported_without_crashing() -> None:
    events = [
        {"run_id": "run-1", "event_id": "event-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_id": "event-1", "event_type": "RUN_END", "seq": 2, "payload": {"status": "completed"}},
    ]
    reasons = validate_lifecycle(events, {"run-1"})
    assert "duplicate_event_id" in reasons


def test_completed_trace_rejects_orphan_model_response(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    review = audit_trace_reference(tmp_path, state)
    assert review["trace_ok"] is False
    assert "orphan_model_response" in review["reasons"]


def test_provider_error_may_end_after_unanswered_request_but_needs_error_event() -> None:
    events = [
        {"run_id": "run-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_type": "MODEL_REQUEST", "seq": 2, "payload": {}},
        {"run_id": "run-1", "event_type": "ERROR", "seq": 3, "payload": {"error": "timeout"}},
        {"run_id": "run-1", "event_type": "RUN_END", "seq": 4, "payload": {"status": "provider_error"}},
    ]
    assert validate_lifecycle(events, {"run-1"}) == []
