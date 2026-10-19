from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.audit_g7_trace_q_consistency import (
    audit_trace_reference,
    build_report,
    classify_recorded_failure,
    validate_lifecycle,
)
from scripts.derive_g7_trace_view import split_attempts
from scripts.run_g7_failure_localization import emit, existing_trace_sequence, state_claim, trace_path_for_retry


def _write_events(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = []
    for index, event in enumerate(events, 1):
        value = dict(event)
        value.setdefault("seq", index)
        value.setdefault("event_id", f"event-{index}")
        value.setdefault("step_id", f"step-{index}")
        if value.get("event_type") in {"MODEL_RESPONSE", "TOOL_RESULT", "TOOL_ERROR"}:
            value.setdefault("parent_step_id", f"step-{index - 1}")
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
        {"run_id": "run-1", "event_id": "event-1", "step_id": "step-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_id": "event-2", "step_id": "step-2", "event_type": "RUN_START", "seq": 2, "payload": {}},
        {"run_id": "run-1", "event_id": "event-3", "step_id": "step-3", "event_type": "MODEL_RESPONSE", "seq": 3, "payload": {}},
        {"run_id": "run-1", "event_id": "event-4", "step_id": "step-4", "event_type": "RUN_END", "seq": 4, "payload": {"status": "completed"}},
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
        {"run_id": "run-1", "event_id": "event-1", "step_id": "step-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_id": "event-1", "step_id": "step-2", "event_type": "RUN_END", "seq": 2, "payload": {"status": "completed"}},
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
        {"run_id": "run-1", "event_id": "event-1", "step_id": "step-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_id": "event-2", "step_id": "step-2", "event_type": "MODEL_REQUEST", "seq": 2, "payload": {}},
        {"run_id": "run-1", "event_id": "event-3", "step_id": "step-3", "event_type": "ERROR", "seq": 3, "payload": {"error": "timeout"}},
        {"run_id": "run-1", "event_id": "event-4", "step_id": "step-4", "event_type": "RUN_END", "seq": 4, "payload": {"status": "provider_error"}},
    ]
    assert validate_lifecycle(events, {"run-1"}) == []


def test_provider_error_record_rejects_completed_run_end(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "provider_error", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "ERROR", "payload": {"error": "timeout"}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    review = audit_trace_reference(tmp_path, state)
    assert review["trace_ok"] is False
    assert "missing_provider_error_run_end" in review["reasons"]
    assert "run_end_status_mismatch" in review["reasons"]


def test_q_coverage_must_match_state_rows_before_confirmatory_reuse(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    report = build_report(states=[state], q_rows=[], trace_root=tmp_path)
    assert report["q"]["states_missing_q_row"] == 1
    assert report["conclusion"]["confirmatory_reuse_allowed"] is False


def test_duplicate_q_rows_fail_closed(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    report = build_report(
        states=[state],
        q_rows=[{"run_id": "run-1", "is_valid": True}, {"run_id": "run-1", "is_valid": True}],
        trace_root=tmp_path,
    )
    assert report["q"]["duplicate_run_ids"] == ["run-1"]
    assert report["conclusion"]["confirmatory_reuse_allowed"] is False


def test_completed_trace_integrity_failure_blocks_confirmatory_reuse_even_for_invalid_q(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    report = build_report(
        states=[state],
        q_rows=[{"run_id": "run-1", "is_valid": False}],
        trace_root=tmp_path,
    )
    assert report["states"]["trace_integrity_failures"] == 1
    assert report["conclusion"]["confirmatory_reuse_allowed"] is False


def test_missing_event_and_step_identity_is_not_accepted() -> None:
    events = [
        {"run_id": "run-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_type": "RUN_END", "seq": 2, "payload": {"status": "completed"}},
    ]
    reasons = validate_lifecycle(events, {"run-1"})
    assert "missing_event_id:1" in reasons
    assert "missing_step_id:2" in reasons


def test_response_parent_step_mismatch_is_not_hidden() -> None:
    events = [
        {"run_id": "run-1", "event_id": "event-1", "step_id": "step-1", "event_type": "RUN_START", "seq": 1, "payload": {}},
        {"run_id": "run-1", "event_id": "event-2", "step_id": "step-2", "event_type": "MODEL_REQUEST", "seq": 2, "payload": {}},
        {"run_id": "run-1", "event_id": "event-3", "step_id": "step-3", "parent_step_id": "wrong", "event_type": "MODEL_RESPONSE", "seq": 3, "payload": {}},
        {"run_id": "run-1", "event_id": "event-4", "step_id": "step-4", "event_type": "RUN_END", "seq": 4, "payload": {"status": "completed"}},
    ]
    reasons = validate_lifecycle(events, {"run-1"})
    assert "model_response_parent_mismatch:3" in reasons


def test_duplicate_state_id_is_not_used_as_an_arbitrary_last_row(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_REQUEST", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    report = build_report(
        states=[state, dict(state)],
        q_rows=[{"run_id": "run-1", "is_valid": True}],
        trace_root=tmp_path,
    )
    assert report["states"]["duplicate_run_ids"] == ["run-1"]
    assert report["q"]["rows_missing_state_review"] == 1
    assert report["q"]["trace_backed_valid"] == 0
    assert report["conclusion"]["confirmatory_reuse_allowed"] is False


def test_duplicate_checkpoint_id_blocks_even_when_checkpoint_traces_are_valid(tmp_path: Path) -> None:
    state = {"run_id": "run-1", "status": "completed", "trace_ref": "traces/run-1/events.jsonl"}
    _write_events(
        tmp_path / "traces/run-1/events.jsonl",
        [
            {"run_id": "run-1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_REQUEST", "payload": {}},
            {"run_id": "run-1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "run-1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    _write_events(
        tmp_path / "traces/checkpoint_c1/events.jsonl",
        [
            {"run_id": "checkpoint_c1", "event_type": "RUN_START", "payload": {}},
            {"run_id": "checkpoint_c1", "event_type": "MODEL_REQUEST", "payload": {}},
            {"run_id": "checkpoint_c1", "event_type": "MODEL_RESPONSE", "payload": {}},
            {"run_id": "checkpoint_c1", "event_type": "RUN_END", "payload": {"status": "completed"}},
        ],
    )
    checkpoint = {"checkpoint_id": "c1", "status": "completed", "trace_ref": "traces/checkpoint_c1/events.jsonl"}
    report = build_report(
        states=[state],
        q_rows=[{"run_id": "run-1", "is_valid": False}],
        checkpoints=[checkpoint, dict(checkpoint)],
        trace_root=tmp_path,
    )
    assert report["checkpoints"]["duplicate_ids"] == ["c1"]
    assert report["checkpoints"]["trace_integrity_failures"] == 0
    assert report["conclusion"]["confirmatory_reuse_allowed"] is False


def test_non_boolean_q_validity_is_malformed_not_truthy() -> None:
    report = build_report(
        states=[],
        q_rows=[{"run_id": "run-1", "is_valid": "false"}],
        trace_root=Path("."),
    )
    assert report["q"]["original_independent_valid"] == 0
    assert report["q"]["malformed_validity_rows"] == 1
    assert report["conclusion"]["confirmatory_reuse_allowed"] is False


def test_g7_emit_persists_identity_and_resumes_sequence(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    seq = emit(path, 0, "run-1", "MODEL_REQUEST", "RUNNING", {})
    seq = emit(path, seq, "run-1", "MODEL_RESPONSE", "COMPLETED", {})
    assert seq == 2
    assert existing_trace_sequence(path) == 2
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["event_id"] == "run-1:event-000001"
    assert rows[1]["step_id"] == "run-1:step-000002"
    assert rows[1]["parent_step_id"] == "run-1:step-000001"
    seq = emit(path, existing_trace_sequence(path), "run-1", "RUN_END", "COMPLETED", {"status": "completed"})
    assert seq == 3
    assert existing_trace_sequence(path) == 3


def test_g7_retry_trace_path_preserves_malformed_history(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "run-1" / "events.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"seq": 1}) + "\n" + json.dumps({"seq": 1}) + "\n",
        encoding="utf-8",
    )

    retry_path, seq = trace_path_for_retry(path)

    assert retry_path != path
    assert retry_path.name == "events.jsonl"
    assert retry_path.parent.name == "run-1.retry-1"
    assert seq == 0
    assert path.read_text(encoding="utf-8").count('"seq": 1') == 2


def test_g7_retry_trace_path_never_appends_to_terminal_history(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "run-1" / "events.jsonl"
    seq = emit(path, 0, "run-1", "RUN_START", "RUNNING", {})
    seq = emit(path, seq, "run-1", "RUN_END", "COMPLETED", {"status": "completed"})
    original = path.read_text(encoding="utf-8")

    retry_path, retry_seq = trace_path_for_retry(path)

    assert retry_path.parent.name == "run-1.retry-1"
    assert retry_seq == 0
    assert not retry_path.exists()
    assert path.read_text(encoding="utf-8") == original


def test_g7_retry_trace_path_skips_existing_retry_history(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "run-1" / "events.jsonl"
    seq = emit(path, 0, "run-1", "RUN_START", "RUNNING", {})
    emit(path, seq, "run-1", "MODEL_REQUEST", "RUNNING", {})
    retry_one = path.parent.parent / "run-1.retry-1" / path.name
    emit(retry_one, 0, "run-1", "RUN_START", "RUNNING", {})
    retry_one_contents = retry_one.read_text(encoding="utf-8")

    retry_path, retry_seq = trace_path_for_retry(path)

    assert retry_path.parent.name == "run-1.retry-2"
    assert retry_seq == 0
    assert retry_one.read_text(encoding="utf-8") == retry_one_contents


def test_g7_retry_trace_path_concurrent_reservations_are_distinct(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "run-1" / "events.jsonl"
    seq = emit(path, 0, "run-1", "RUN_START", "RUNNING", {})
    emit(path, seq, "run-1", "MODEL_REQUEST", "RUNNING", {})

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: trace_path_for_retry(path), range(2)))

    paths = [result[0] for result in results]
    assert len({candidate.parent.name for candidate in paths}) == 2
    assert {candidate.parent.name for candidate in paths} == {"run-1.retry-1", "run-1.retry-2"}
    assert all(result[1] == 0 for result in results)
    assert path.read_text(encoding="utf-8").count("MODEL_REQUEST") == 1


def test_g7_derived_view_splits_every_run_start_without_pooling(tmp_path: Path) -> None:
    events = [
        {"run_id": "run-1", "event_type": "RUN_START"},
        {"run_id": "run-1", "event_type": "MODEL_REQUEST"},
        {"run_id": "run-1", "event_type": "RUN_START"},
        {"run_id": "run-1", "event_type": "MODEL_RESPONSE"},
        {"run_id": "run-1", "event_type": "RUN_END"},
    ]

    attempts = split_attempts(events)

    assert len(attempts) == 2
    assert [event["event_type"] for event in attempts[0]] == ["RUN_START", "MODEL_REQUEST"]
    assert [event["event_type"] for event in attempts[1]] == ["RUN_START", "MODEL_RESPONSE", "RUN_END"]


def test_g7_terminal_error_recovers_sequence_after_inner_loop_failure(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    seq = emit(path, 0, "run-1", "RUN_START", "RUNNING", {})
    seq = emit(path, seq, "run-1", "MODEL_REQUEST", "RUNNING", {})

    # This mirrors the outer runner's exception path when the provider raises
    # inside public_tool_loop before returning its local sequence to the caller.
    seq = existing_trace_sequence(path)
    seq = emit(path, seq, "run-1", "ERROR", "FAILED", {"error_type": "RuntimeError"})
    seq = emit(path, seq, "run-1", "RUN_END", "FAILED", {"status": "provider_error"})
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert [row["seq"] for row in rows] == [1, 2, 3, 4]
    assert validate_lifecycle(rows, {"run-1"}) == []


def test_g7_state_claim_is_atomic_and_released(tmp_path: Path) -> None:
    with state_claim(tmp_path, "run-1") as first:
        assert first is True
        with state_claim(tmp_path, "run-1") as second:
            assert second is False
    with state_claim(tmp_path, "run-1") as reclaimed:
        assert reclaimed is True
