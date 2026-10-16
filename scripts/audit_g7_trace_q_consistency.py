#!/usr/bin/env python3
"""Cross-check persisted G7 Q decisions against their append-only traces.

This is a derived, read-only audit. It never changes state/Q rows, retries a
provider call, or pools a retry with another run. The existing Q audit checks
the scientific labels independently; this audit adds the missing execution
evidence check that a Q-valid row must reference a completed, error-free trace.
Failure categories describe recorded error text only and are not provider
root-cause claims.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_ERROR_MARKERS = (
    "no valid json",
    "provider response did not contain a json object",
    "missing stage",
    "missing stages",
    "invalid decision",
    "invalid v verdict",
)
TRANSPORT_ERROR_MARKERS = (
    "provider request failed",
    "http ",
    "urlerror",
    "timeout",
    "connection",
)


def readl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _trace_path(root: Path, trace_ref: Any) -> tuple[Path | None, str | None]:
    if not isinstance(trace_ref, str) or not trace_ref:
        return None, "missing_trace_ref"
    # Historical JSONL was produced on Windows and uses backslashes. Normalize
    # them so the read-only audit remains portable and path traversal-safe.
    relative = Path(*trace_ref.replace("\\", "/").split("/"))
    root = root.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        return None, "trace_path_outside_root"
    if not candidate.is_file():
        return candidate, "trace_file_missing"
    return candidate, None


def _load_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"malformed_json_line:{line_number}")
            continue
        if not isinstance(value, dict):
            errors.append(f"non_object_line:{line_number}")
            continue
        events.append(value)
    return events, errors


def _error_text(events: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for event in events:
        if event.get("event_type") != "ERROR":
            continue
        payload = event.get("payload") or {}
        if isinstance(payload, dict):
            values.append(str(payload.get("error", "")))
            values.append(str(payload.get("error_type", "")))
    return [value for value in values if value and value.lower() != "none"]


def _canonical_id(value: Any) -> str:
    """Return a usable persisted identifier, or the empty sentinel."""
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _duplicate_ids(values: list[str]) -> list[str]:
    counts = collections.Counter(values)
    return sorted(value for value, count in counts.items() if count > 1 or not value)


def _unique_index(values: list[str], rows: list[dict[str, Any]],
                  duplicate_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Index only unambiguous, non-empty IDs.

    A dict comprehension would silently select the last duplicate row. That
    is unsafe for a derived audit because a later malformed row could replace
    the trace/Q evidence belonging to an earlier row. Ambiguous IDs are
    deliberately omitted and are reported by the caller as non-bijective.
    """
    duplicate_set = set(duplicate_ids)
    return {
        identifier: row
        for identifier, row in zip(values, rows)
        if identifier and identifier not in duplicate_set
    }


def _segments(events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split append-only history at a new run after the previous run ended.

    A second ``RUN_END`` or ``RUN_START`` inside one segment is malformed
    lifecycle history, not a new retry.  Keeping it in the same segment lets
    the lifecycle validator reject it instead of silently selecting a suffix.
    """
    segments: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for event in events:
        if (event.get("event_type") == "RUN_START" and current
                and current[-1].get("event_type") == "RUN_END"):
            segments.append(current)
            current = []
        current.append(event)
    if current:
        segments.append(current)
    return segments


def classify_recorded_failure(errors: list[str]) -> str:
    """Classify persisted error text without inferring an external root cause."""
    text = " ".join(errors).lower()
    if not text:
        return "none"
    if "hard budget" in text:
        return "hard_budget_limit"
    if any(marker in text for marker in CONTRACT_ERROR_MARKERS):
        return "response_contract_failure"
    if any(marker in text for marker in TRANSPORT_ERROR_MARKERS):
        return "transport_or_provider_failure"
    return "recorded_runner_failure"


def validate_lifecycle(events: list[dict[str, Any]], expected_run_ids: set[str]) -> list[str]:
    """Validate the G7 append-only event contract for one selected segment.

    This is deliberately a trace-integrity check, not a provider diagnosis.
    G7 emits ``seq`` rather than the generic ``sequence`` field used by some
    other runners, so missing, duplicated, or out-of-order sequence values
    are evidence failures.  A provider exception may leave its model request
    without a response; that is valid only for a terminal provider-error
    segment with an explicit ERROR event.
    """
    reasons: list[str] = []
    if not events:
        return ["empty_trace_segment"]

    event_types = [str(event.get("event_type", "")) for event in events]
    starts = [index for index, value in enumerate(event_types) if value == "RUN_START"]
    ends = [index for index, value in enumerate(event_types) if value == "RUN_END"]
    if event_types[0] != "RUN_START":
        reasons.append("first_event_not_run_start")
    if event_types[-1] != "RUN_END":
        reasons.append("last_event_not_run_end")
    if len(starts) != 1:
        reasons.append(f"run_start_count:{len(starts)}")
    if len(ends) != 1:
        reasons.append(f"run_end_count:{len(ends)}")
    if starts and starts[0] != 0:
        reasons.append("run_start_not_first")
    if ends and ends[0] != len(events) - 1:
        reasons.append("run_end_not_last")

    sequences: list[int] = []
    for index, event in enumerate(events, 1):
        value = event.get("seq", event.get("sequence"))
        if isinstance(value, bool) or not isinstance(value, int):
            reasons.append(f"missing_or_invalid_sequence:{index}")
            continue
        sequences.append(value)
    if len(sequences) == len(events):
        if len(set(sequences)) != len(sequences):
            reasons.append("duplicate_sequence")
        if any(current <= previous for previous, current in zip(sequences, sequences[1:])):
            reasons.append("sequence_not_strictly_increasing")

    # Event and step identities are part of the immutable pairing contract.
    # Missing IDs used to pass because the duplicate check only considered IDs
    # that happened to be present.
    event_ids: list[str] = []
    step_ids: list[str] = []
    for index, event in enumerate(events, 1):
        event_id = _canonical_id(event.get("event_id"))
        step_id = _canonical_id(event.get("step_id"))
        if not event_id:
            reasons.append(f"missing_event_id:{index}")
        else:
            event_ids.append(event_id)
        if not step_id:
            reasons.append(f"missing_step_id:{index}")
        else:
            step_ids.append(step_id)
        parent_step_id = event.get("parent_step_id")
        if parent_step_id is not None and not _canonical_id(parent_step_id):
            reasons.append(f"invalid_parent_step_id:{index}")
    if len(event_ids) != len(set(event_ids)):
        reasons.append("duplicate_event_id")
    if len(step_ids) != len(set(step_ids)):
        reasons.append("duplicate_step_id")

    observed_run_ids = {str(event.get("run_id", "")) for event in events}
    if not observed_run_ids.issubset(expected_run_ids):
        reasons.append("trace_run_id_mismatch")

    end_status = str((events[-1].get("payload") or {}).get("status", "")) if ends else ""
    pending_models = 0
    pending_tools = 0
    for event_type in event_types:
        if event_type == "MODEL_REQUEST":
            pending_models += 1
        elif event_type == "MODEL_RESPONSE":
            if pending_models == 0:
                reasons.append("orphan_model_response")
            else:
                pending_models -= 1
        elif event_type == "TOOL_CALL":
            pending_tools += 1
        elif event_type in {"TOOL_RESULT", "TOOL_ERROR"}:
            if pending_tools == 0:
                reasons.append("orphan_tool_result")
            else:
                pending_tools -= 1

    # A count-only check permits a response to be paired with the wrong
    # request when events are reordered or duplicated. Validate the explicit
    # parent step IDs as well. The runner emits one request/call before each
    # corresponding response/result, so FIFO pairing is deterministic.
    pending_model_steps: list[str] = []
    pending_tool_steps: list[str] = []
    for index, event in enumerate(events, 1):
        event_type = event.get("event_type")
        step_id = _canonical_id(event.get("step_id"))
        parent_step_id = _canonical_id(event.get("parent_step_id"))
        if event_type == "MODEL_REQUEST":
            if step_id:
                pending_model_steps.append(step_id)
        elif event_type == "MODEL_RESPONSE":
            if pending_model_steps:
                expected = pending_model_steps.pop(0)
                if not parent_step_id:
                    reasons.append(f"missing_model_response_parent:{index}")
                elif parent_step_id != expected:
                    reasons.append(f"model_response_parent_mismatch:{index}")
        elif event_type == "TOOL_CALL":
            if step_id:
                pending_tool_steps.append(step_id)
        elif event_type in {"TOOL_RESULT", "TOOL_ERROR"}:
            if pending_tool_steps:
                expected = pending_tool_steps.pop(0)
                if not parent_step_id:
                    reasons.append(f"missing_tool_result_parent:{index}")
                elif parent_step_id != expected:
                    reasons.append(f"tool_result_parent_mismatch:{index}")
    if end_status == "completed":
        if pending_models:
            reasons.append("unmatched_model_request")
        if pending_tools:
            reasons.append("unmatched_tool_call")
    elif end_status == "provider_error":
        if pending_tools:
            reasons.append("unmatched_tool_call")

    # Preserve order while avoiding repeated reasons from a malformed trace.
    return list(dict.fromkeys(reasons))


def audit_trace_reference(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    """Return execution evidence for one state/checkpoint record."""
    run_id = str(record.get("run_id", record.get("checkpoint_id", "")))
    status = str(record.get("status", ""))
    trace_path, path_error = _trace_path(root, record.get("trace_ref"))
    if path_error:
        if status == "checkpoint_missing" and path_error == "missing_trace_ref":
            return {"run_id": run_id, "record_status": status, "trace_status": "not_executed",
                    "trace_ok": True, "failure_category": "none", "reasons": []}
        return {"run_id": run_id, "record_status": status, "trace_status": path_error,
                "trace_ok": False, "failure_category": "trace_evidence_missing",
                "reasons": [path_error]}

    assert trace_path is not None
    events, parse_errors = _load_events(trace_path)
    segments = _segments(events)
    canonical_events = segments[-1] if segments else []
    errors = _error_text(canonical_events)
    event_run_ids = sorted({str(event.get("run_id", "")) for event in canonical_events})
    expected_run_ids = {run_id}
    if "run_id" not in record and record.get("checkpoint_id"):
        expected_run_ids.add(f"checkpoint_{run_id}")
    run_id_mismatch = any(value not in expected_run_ids for value in event_run_ids)
    starts = [event for event in canonical_events if event.get("event_type") == "RUN_START"]
    ends = [event for event in canonical_events if event.get("event_type") == "RUN_END"]
    completed_end = any((event.get("payload") or {}).get("status") == "completed" for event in ends)
    failed_end = any((event.get("payload") or {}).get("status") == "provider_error" for event in ends)
    has_model_response = any(event.get("event_type") == "MODEL_RESPONSE" for event in canonical_events)
    lifecycle_reasons = validate_lifecycle(canonical_events, expected_run_ids)
    common = {
        "run_id": run_id,
        "record_status": status,
        "trace_ref": str(record.get("trace_ref")),
        "event_count": len(canonical_events),
        "history_segment_count": len(segments),
        "event_run_ids": event_run_ids,
        "error_count": len(errors),
        "error_text": errors,
        "failure_category": classify_recorded_failure(errors),
        "parse_errors": parse_errors,
        "event_type_counts": dict(collections.Counter(event.get("event_type", "") for event in canonical_events)),
        "lifecycle_reasons": lifecycle_reasons,
    }
    if status == "completed":
        reasons = list(lifecycle_reasons)
        if parse_errors:
            reasons.extend(parse_errors)
        if run_id_mismatch:
            reasons.append("trace_run_id_mismatch")
        if not starts:
            reasons.append("missing_run_start")
        if not completed_end:
            reasons.append("missing_completed_run_end")
        if failed_end:
            reasons.append("run_end_status_mismatch")
        if errors:
            reasons.append("error_event_in_completed_trace")
        if not has_model_response:
            reasons.append("missing_model_response")
        return {**common, "trace_status": "pass" if not reasons else "trace_inconsistent",
                "trace_ok": not reasons, "reasons": reasons}
    if status == "provider_error":
        reasons = list(lifecycle_reasons)
        if parse_errors:
            reasons.extend(parse_errors)
        if run_id_mismatch:
            reasons.append("trace_run_id_mismatch")
        if not starts:
            reasons.append("missing_run_start")
        if not failed_end:
            reasons.append("missing_provider_error_run_end")
        if completed_end:
            reasons.append("run_end_status_mismatch")
        if not errors and not failed_end:
            reasons.append("missing_failure_evidence")
        return {**common, "trace_status": "terminal_failure_evidence" if not reasons else "failure_trace_inconsistent",
                "trace_ok": not reasons, "reasons": reasons}
    return {**common, "trace_status": "unrecognized_state_status", "trace_ok": False,
            "reasons": [f"unrecognized_state_status:{status}"]}


def build_report(*, states: list[dict[str, Any]], q_rows: list[dict[str, Any]],
                 trace_root: Path, checkpoints: list[dict[str, Any]] | None = None,
                 input_hashes: dict[str, str | None] | None = None) -> dict[str, Any]:
    state_ids = [_canonical_id(row.get("run_id")) for row in states]
    duplicate_state_ids = _duplicate_ids(state_ids)
    state_by_id = _unique_index(state_ids, states, duplicate_state_ids)
    state_reviews = [audit_trace_reference(trace_root, row) for row in states]
    state_review_by_id = _unique_index(state_ids, state_reviews, duplicate_state_ids)
    q_ids = [_canonical_id(row.get("run_id")) for row in q_rows]
    duplicate_q_ids = _duplicate_ids(q_ids)
    state_id_set = set(state_ids)
    q_id_set = set(q_ids)
    q_missing_for_state = sorted(state_id_set - q_id_set)
    q_extra_rows = sorted(q_id_set - state_id_set)
    q_original_valid = sum(row.get("is_valid") is True for row in q_rows)
    q_malformed_validity = sum(not isinstance(row.get("is_valid"), bool) for row in q_rows)
    q_trace_backed_valid = 0
    q_invalidated = 0
    q_missing_state = 0
    q_review_statuses: collections.Counter[str] = collections.Counter()
    for row in q_rows:
        run_id = _canonical_id(row.get("run_id"))
        state = state_by_id.get(run_id)
        review = state_review_by_id.get(run_id)
        if state is None or review is None:
            q_missing_state += 1
            q_review_statuses["missing_state"] += 1
        elif row.get("is_valid") is True and review.get("trace_ok"):
            q_trace_backed_valid += 1
            q_review_statuses["trace_backed_valid"] += 1
        elif row.get("is_valid") is True:
            q_invalidated += 1
            q_review_statuses[str(review.get("trace_status"))] += 1
        elif not isinstance(row.get("is_valid"), bool):
            q_review_statuses["malformed_validity"] += 1
        else:
            q_review_statuses["q_invalid_preserved"] += 1

    checkpoint_reviews = []
    if checkpoints is not None:
        checkpoint_reviews = [audit_trace_reference(trace_root, row) for row in checkpoints]
    checkpoint_ids = [
        _canonical_id(row.get("checkpoint_id", row.get("run_id")))
        for row in checkpoints or []
    ]
    duplicate_checkpoint_ids = _duplicate_ids(checkpoint_ids) if checkpoints is not None else []
    state_status_counts = collections.Counter(str(row.get("status")) for row in states)
    trace_status_counts = collections.Counter(str(row.get("trace_status")) for row in state_reviews)
    failure_category_counts = collections.Counter(str(row.get("failure_category")) for row in state_reviews)
    checkpoint_status_counts = collections.Counter(str(row.get("status")) for row in checkpoints or [])
    checkpoint_trace_status_counts = collections.Counter(str(row.get("trace_status")) for row in checkpoint_reviews)
    checkpoint_failure_category_counts = collections.Counter(
        str(row.get("failure_category")) for row in checkpoint_reviews
    )
    terminal_states = sum(count for status, count in state_status_counts.items() if status != "completed")
    terminal_checkpoints = sum(count for status, count in checkpoint_status_counts.items() if status != "completed")
    state_trace_integrity_failures = sum(not row.get("trace_ok") for row in state_reviews)
    checkpoint_trace_integrity_failures = sum(not row.get("trace_ok") for row in checkpoint_reviews)
    return {
        "audit_version": "g7-trace-q-consistency-v4",
        "audit_scope": "read_only_trace_lifecycle_q_cross_check; no_provider_call; no_scientific_truth_decision",
        "trace_policy": "audit_latest_append_only_RUN_START_to_RUN_END_segment; require_unique_event_step_ids_and_parent_pairing; retain_prior_history_count",
        "inputs": input_hashes or {},
        "states": {
            "rows": len(states),
            "unique_run_ids": len(state_id_set),
            "duplicate_run_ids": duplicate_state_ids,
            "status_counts": dict(state_status_counts),
            "trace_status_counts": dict(trace_status_counts),
            "recorded_failure_category_counts": dict(failure_category_counts),
            "trace_integrity_failures": state_trace_integrity_failures,
            "reviews": state_reviews,
            "review_samples": [row for row in state_reviews if row.get("record_status") != "completed" or not row.get("trace_ok")][:20],
        },
        "checkpoints": {
            "provided": checkpoints is not None,
            "rows": len(checkpoints or []),
            "unique_ids": len(set(checkpoint_ids)),
            "duplicate_ids": duplicate_checkpoint_ids,
            "status_counts": dict(checkpoint_status_counts),
            "trace_status_counts": dict(checkpoint_trace_status_counts),
            "recorded_failure_category_counts": dict(checkpoint_failure_category_counts),
            "trace_integrity_failures": checkpoint_trace_integrity_failures,
            "reviews": checkpoint_reviews,
            "review_samples": [row for row in checkpoint_reviews if row.get("record_status") != "completed" or not row.get("trace_ok")][:20],
        },
        "q": {
            "rows": len(q_rows),
            "unique_run_ids": len(q_id_set),
            "original_independent_valid": q_original_valid,
            "trace_backed_valid": q_trace_backed_valid,
            "valid_rows_invalidated_by_trace_review": q_invalidated,
            "rows_missing_state_review": q_missing_state,
            "states_missing_q_row": len(q_missing_for_state),
            "q_rows_without_state": len(q_extra_rows),
            "duplicate_run_ids": duplicate_q_ids,
            "malformed_validity_rows": q_malformed_validity,
            "review_status_counts": dict(q_review_statuses),
        },
        "conclusion": {
            "terminal_failures_retained": terminal_states > 0 or terminal_checkpoints > 0,
            "q_invalidity_retained": bool(q_rows) and not q_malformed_validity,
            "retries_pooled": False,
            "confirmatory_reuse_allowed": not any((
                terminal_states,
                terminal_checkpoints,
                state_trace_integrity_failures,
                checkpoint_trace_integrity_failures,
                q_invalidated,
                q_missing_state,
                bool(duplicate_state_ids),
                bool(duplicate_q_ids),
                bool(duplicate_checkpoint_ids),
                q_malformed_validity,
                bool(q_missing_for_state),
                bool(q_extra_rows),
                len(q_rows) != len(states),
            )),
            "scientific_truth_decision_made": False,
            "interpretation_boundary": "Failure categories are derived from persisted trace text; they do not establish an external provider root cause or scientific validity.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--q", type=Path, required=True)
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    states = readl(args.states)
    q_rows = readl(args.q)
    checkpoints = readl(args.checkpoints) if args.checkpoints else None
    report = build_report(
        states=states,
        q_rows=q_rows,
        trace_root=args.trace_root,
        checkpoints=checkpoints,
        input_hashes={
            "states": sha256(args.states),
            "q": sha256(args.q),
            "checkpoints": sha256(args.checkpoints) if args.checkpoints else None,
        },
    )
    report["trace_root"] = str(args.trace_root.resolve())
    report["audit_script_sha256"] = sha256(Path(__file__).resolve())
    # Persist a compact derived report. The in-memory report retains every
    # review for callers/tests, while the on-disk artifact keeps only counts
    # and bounded anomaly samples; raw provider payloads remain untouched.
    persisted_report = json.loads(json.dumps(report, ensure_ascii=False))
    persisted_report["states"].pop("reviews", None)
    persisted_report["checkpoints"].pop("reviews", None)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(persisted_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "states": report["states"]["rows"],
        "terminal_failures_retained": report["conclusion"]["terminal_failures_retained"],
        "q_original_independent_valid": report["q"]["original_independent_valid"],
        "q_trace_backed_valid": report["q"]["trace_backed_valid"],
        "q_invalidated_by_trace_review": report["q"]["valid_rows_invalidated_by_trace_review"],
        "confirmatory_reuse_allowed": report["conclusion"]["confirmatory_reuse_allowed"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
