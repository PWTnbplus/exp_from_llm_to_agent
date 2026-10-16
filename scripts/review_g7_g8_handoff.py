#!/usr/bin/env python3
"""Independent, source-only G7 review and G8 checkpoint reconstruction.

This audit deliberately does not load the private G6/G7 oracle or any answer
key.  It verifies the public-input boundary and the append-only provider trace,
then copies the exact public messages from the real G7 checkpoint request.
The resulting checkpoint file is a derived view; the original G7 artifacts are
never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "expected_decision", "correct_revised_claim", "oracle_reason", "private_oracle",
    "V_true", "L_true_impacted_nodes", "U_true_node_changes", "ground_truth",
    "source_g6_oracle", "answer_key",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _required_id(row: dict[str, Any], field: str, label: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} has missing or invalid {field}")
    return value


def index_unique(rows: list[dict[str, Any]], key, label: str) -> dict[Any, dict[str, Any]]:
    indexed: dict[Any, dict[str, Any]] = {}
    for row in rows:
        value = key(row)
        if value in indexed:
            raise ValueError(f"duplicate {label}: {value!r}")
        indexed[value] = row
    return indexed


def find_forbidden(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN:
                errors.append(f"{path}.{key}")
            errors.extend(find_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(find_forbidden(child, f"{path}[{index}]"))
    return errors


def trace_events(root: Path, ref: str) -> tuple[Path, list[dict[str, Any]]]:
    # G7 stores Windows separators even when the artifact is consumed on a
    # POSIX-like host.  Resolve only within the audited root.
    event_path = root / Path(ref.replace("\\", "/"))
    if not event_path.is_file():
        raise FileNotFoundError(event_path)
    return event_path, read_jsonl(event_path)


def public_checkpoint(row: dict[str, Any], root: Path, event_path: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    request_events = [
        event for event in events
        if event.get("event_type") == "MODEL_REQUEST"
        and event.get("payload", {}).get("checkpoint") is True
    ]
    if row.get("status") != "completed":
        raise ValueError("provider-error checkpoint has no usable public messages")
    if not request_events:
        raise ValueError("expected at least one checkpoint MODEL_REQUEST")
    # Later requests in one checkpoint trace contain tool results and the G3
    # synthesis prompt.  G8 must enter at the first pre-mechanism checkpoint.
    event = request_events[0]
    payload = event.get("payload", {})
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("checkpoint MODEL_REQUEST has no public messages")
    leaks = find_forbidden(messages, "$.public_messages")
    if leaks:
        raise ValueError("forbidden field in public messages: " + ", ".join(leaks))
    for request_event in request_events:
        leaks = find_forbidden(request_event.get("payload", {}).get("messages", []), "$.trace.messages")
        if leaks:
            raise ValueError("forbidden field in trace messages: " + ", ".join(leaks))
    seqs = [event.get("seq") for event in events]
    if seqs != list(range(1, len(events) + 1)):
        raise ValueError("trace sequence is not contiguous and monotonic")
    if not any(event.get("event_type") == "MODEL_RESPONSE" for event in events):
        raise ValueError("checkpoint trace has no model response")
    if not any(event.get("event_type") == "RUN_END" and event.get("status") == "COMPLETED" for event in events):
        raise ValueError("checkpoint trace has no completed RUN_END")
    return {
        "checkpoint_id": row["checkpoint_id"],
        "case_id": row["case_id"],
        "group_id": row["group_id"],
        "replicate": 0,
        "initial_decision": row["initial_decision"],
        "public_messages": messages,
        "trace_ref": str(event_path.relative_to(root)).replace("/", "\\"),
        "trace_sha256": sha256(event_path),
        "status": "completed",
        "public_only": True,
        "source": "g7_real_checkpoint_MODEL_REQUEST",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g7-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.g7_root.resolve()
    out = args.out_dir.resolve()
    public_path = root / "g7_public_cases.jsonl"
    checkpoints_path = root / "g7_checkpoints.jsonl"
    public = read_jsonl(public_path)
    checkpoints = read_jsonl(checkpoints_path)
    errors: list[str] = []
    public_by_case = index_unique(
        public,
        lambda row: _required_id(row, "case_id", "public row"),
        "public case_id",
    )
    checkpoint_by_pair = index_unique(
        checkpoints,
        lambda row: (
            _required_id(row, "case_id", "checkpoint row"),
            _required_id(row, "group_id", "checkpoint row"),
        ),
        "checkpoint case/group",
    )
    index_unique(
        checkpoints,
        lambda row: _required_id(row, "checkpoint_id", "checkpoint row"),
        "checkpoint_id",
    )
    case_ids = set(public_by_case)
    families = {row.get("theory_family_id") for row in public}
    if len(public) != 92:
        errors.append(f"expected 92 public cases, found {len(public)}")
    if len(families) != 23:
        errors.append(f"expected 23 theory families, found {len(families)}")
    if len(case_ids) != len(public):
        errors.append("duplicate public case_id")
    for row in public:
        if row.get("is_mock") or row.get("is_demo"):
            errors.append(f"mock/demo public case: {row.get('case_id')}")
        errors.extend(find_forbidden(row.get("model_visible", {}), f"$.{row.get('case_id')}.model_visible"))

    checkpoint_rows: list[dict[str, Any]] = []
    trace_status = Counter()
    trace_errors: list[str] = []
    completed_by_cf = Counter()
    for row in checkpoint_by_pair.values():
        case_id = row.get("case_id")
        if case_id not in public_by_case:
            errors.append(f"checkpoint references unknown case: {case_id}")
            continue
        status = row.get("status", "missing")
        trace_status[status] += 1
        if status != "completed":
            continue
        try:
            event_path, events = trace_events(root, row["trace_ref"])
            derived = public_checkpoint(row, root, event_path, events)
            checkpoint_rows.append(derived)
            completed_by_cf[public_by_case[case_id].get("cf_type")] += 1
        except (KeyError, ValueError, FileNotFoundError) as exc:
            trace_errors.append(f"{row.get('checkpoint_id')}: {exc}")

    # G8's preregistered main design is CF1/CF2.  Keep all audited public
    # checkpoints in the audit, but expose only these two strata to the plan.
    g8_checkpoints = [
        row for row in checkpoint_rows
        if public_by_case[row["case_id"]].get("cf_type") in {"CF1", "CF2"}
    ]
    g8_checkpoints.sort(key=lambda row: (row["case_id"], row["group_id"]))
    if not g8_checkpoints:
        errors.append("no completed CF1/CF2 public checkpoints")
    checkpoint_index = {(r["case_id"], r["group_id"], r["replicate"]) for r in g8_checkpoints}
    expected_pairs = {
        (row["case_id"], group, 0)
        for row in public
        if row.get("cf_type") in {"CF1", "CF2"}
        for group in ("G3", "G4")
    }
    missing_pairs = sorted(expected_pairs - checkpoint_index)
    audit = {
        "audit_name": "g7_to_g8_source_only_trace_review",
        "status": "REAL_TRACE_AUDITED" if not errors and not trace_errors else "TRACE_REVIEW_FAILED",
        "scientific_selection": "not performed by this structural audit",
        "g7_root": str(root),
        "public_sha256": sha256(public_path),
        "checkpoints_sha256": sha256(checkpoints_path),
        "public_cases": len(public),
        "theory_families": len(families),
        "checkpoint_rows": len(checkpoints),
        "trace_status_counts": dict(trace_status),
        "completed_public_checkpoints_by_cf": dict(completed_by_cf),
        "g8_cf1_cf2_checkpoint_rows": len(g8_checkpoints),
        "expected_cf1_cf2_checkpoint_pairs": len(expected_pairs),
        "missing_cf1_cf2_checkpoint_pairs": missing_pairs,
        "errors": errors,
        "trace_errors": trace_errors,
        "private_oracle_loaded": False,
        "answer_key_loaded": False,
        "warning": "Trace authenticity, billing, immutable weights and mathematical truth still require separate scientific/provider review.",
    }
    write_json(out / "g7_g8_trace_review.json", audit)
    write_jsonl(out / "g8_public_checkpoints.jsonl", g8_checkpoints)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["status"] == "REAL_TRACE_AUDITED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
