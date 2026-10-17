"""Derive an append-only G7 trace view without changing raw provider evidence.

The historical runner sometimes appended a retry to the original JSONL file.
This utility treats every RUN_START as an attempt boundary, keeps only the
final attempt for a record, and accepts it only when the existing lifecycle
validator can prove a self-consistent terminal attempt.  Invalid final
attempts are copied to the derived view for diagnosis, never silently repaired
or pooled with an earlier attempt.  Raw traces remain byte-for-byte untouched.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.audit_g7_trace_q_consistency import (
        _load_events,
        _trace_path,
        readl,
        sha256,
        validate_lifecycle,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script invocation
    from audit_g7_trace_q_consistency import (  # type: ignore[no-redef]
        _load_events,
        _trace_path,
        readl,
        sha256,
        validate_lifecycle,
    )


def split_attempts(events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split an append-only trace at every RUN_START, including malformed ones."""
    attempts: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for event in events:
        if event.get("event_type") == "RUN_START" and current:
            attempts.append(current)
            current = []
        current.append(event)
    if current:
        attempts.append(current)
    return attempts


def _record_id(record: dict[str, Any], ordinal: int) -> str:
    value = record.get("run_id", record.get("checkpoint_id"))
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"missing-record-{ordinal:04d}"


def _safe_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _expected_run_ids(record: dict[str, Any], record_id: str) -> set[str]:
    expected = {record_id}
    if "run_id" not in record and record.get("checkpoint_id"):
        expected.add(f"checkpoint_{record_id}")
    return expected


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _derive_record(
    *,
    record: dict[str, Any],
    ordinal: int,
    trace_root: Path,
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record_id = _record_id(record, ordinal)
    raw_path, path_error = _trace_path(trace_root, record.get("trace_ref"))
    manifest: dict[str, Any] = {
        "record_id": record_id,
        "run_id": record.get("run_id"),
        "checkpoint_id": record.get("checkpoint_id"),
        "worker_index": record.get("worker_index"),
        "attempt_id": record.get("attempt_id"),
        "record_status": record.get("status"),
        "raw_trace_ref": record.get("trace_ref"),
        "raw_trace_sha256": sha256(raw_path) if raw_path and raw_path.is_file() else None,
        "path_error": path_error,
        "attempt_boundary": "every_RUN_START",
        "selected_attempt_index": None,
        "attempt_count": 0,
        "accepted": False,
        "validation_reasons": [],
        "derived_trace_ref": None,
    }
    derived = dict(record)
    if path_error or raw_path is None:
        derived["trace_ref"] = None
        return derived, manifest

    events, parse_errors = _load_events(raw_path)
    attempts = split_attempts(events)
    manifest["attempt_count"] = len(attempts)
    if not attempts:
        manifest["validation_reasons"] = [*parse_errors, "empty_trace"]
        derived["trace_ref"] = None
        return derived, manifest

    selected_index = len(attempts) - 1
    selected = attempts[selected_index]
    expected = _expected_run_ids(record, record_id)
    reasons = [*parse_errors, *validate_lifecycle(selected, expected)]
    end_statuses = [
        (event.get("payload") or {}).get("status")
        for event in selected
        if event.get("event_type") == "RUN_END"
    ]
    terminal_status = end_statuses[-1] if end_statuses else None
    if terminal_status != record.get("status"):
        reasons.append(f"terminal_status_mismatch:{terminal_status}")
    reasons = list(dict.fromkeys(str(reason) for reason in reasons))
    accepted = not reasons

    relative = Path("traces") / _safe_component(record_id) / "events.jsonl"
    destination = output_root / relative
    _write_jsonl(destination, selected)
    derived["trace_ref"] = relative.as_posix()
    manifest.update({
        "selected_attempt_index": selected_index,
        "selected_event_count": len(selected),
        "terminal_status": terminal_status,
        "accepted": accepted,
        "validation_reasons": reasons,
        "derived_trace_ref": relative.as_posix(),
        "derived_trace_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    })
    return derived, manifest


def derive(
    *,
    states: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]] | None,
    trace_root: Path,
    output_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None, list[dict[str, Any]]]:
    derived_states: list[dict[str, Any]] = []
    derived_checkpoints: list[dict[str, Any]] | None = [] if checkpoints is not None else None
    manifest: list[dict[str, Any]] = []
    for ordinal, record in enumerate(states, 1):
        derived, entry = _derive_record(
            record=record, ordinal=ordinal, trace_root=trace_root, output_root=output_root
        )
        derived_states.append(derived)
        entry["record_kind"] = "state"
        manifest.append(entry)
    for ordinal, record in enumerate(checkpoints or [], 1):
        derived, entry = _derive_record(
            record=record, ordinal=ordinal, trace_root=trace_root, output_root=output_root
        )
        assert derived_checkpoints is not None
        derived_checkpoints.append(derived)
        entry["record_kind"] = "checkpoint"
        manifest.append(entry)
    return derived_states, derived_checkpoints, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path)
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()

    states = readl(args.states)
    checkpoints = readl(args.checkpoints) if args.checkpoints else None
    args.out_root.mkdir(parents=True, exist_ok=True)
    derived_states, derived_checkpoints, manifest = derive(
        states=states,
        checkpoints=checkpoints,
        trace_root=args.trace_root,
        output_root=args.out_root,
    )
    _write_jsonl(args.out_root / "states_canonical.jsonl", derived_states)
    if derived_checkpoints is not None:
        _write_jsonl(args.out_root / "checkpoints_canonical.jsonl", derived_checkpoints)
    _write_jsonl(args.out_root / "trace_selection_manifest.jsonl", manifest)
    summary = {
        "states": len(states),
        "checkpoints": len(checkpoints or []),
        "accepted_states": sum(
            entry["accepted"] for entry in manifest if entry["record_kind"] == "state"
        ),
        "accepted_checkpoints": sum(
            entry["accepted"] for entry in manifest if entry["record_kind"] == "checkpoint"
        ),
        "rejection_reason_counts": dict(collections.Counter(
            reason
            for entry in manifest
            if not entry["accepted"]
            for reason in entry["validation_reasons"]
        )),
        "raw_traces_modified": False,
        "output_root": str(args.out_root.resolve()),
    }
    (args.out_root / "derivation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
