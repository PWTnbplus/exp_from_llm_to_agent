#!/usr/bin/env python3
"""Read-only validator for a G5 answer-given run directory."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


EVENT_TYPES = {
    "RUN_START", "MODEL_REQUEST", "MODEL_RESPONSE", "MODEL_ERROR", "MODEL_RETRY",
    "TOOL_CALL", "TOOL_RESULT", "TOOL_ERROR", "STEP_START", "STEP_END",
    "CLAIM_UPDATE", "PREDICTION", "EVALUATION", "CHECKPOINT", "ERROR",
    "POLICY_VIOLATION", "RUN_END",
}
SECRET_RE = re.compile(r"(?i)\b(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})")
PRIVATE_KEY_RE = re.compile(r'(?i)"(?:ground_truth|answer_key|verification_code|verification_status)"\s*:')


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def check_events(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {"events": 0, "errors": [f"read failed: {exc}"]}
    for index, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("event is not an object")
            rows.append(row)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"line {index}: invalid JSON: {exc}")
    seqs = [row.get("seq") for row in rows]
    if seqs != list(range(1, len(rows) + 1)):
        errors.append("sequence is not contiguous from 1")
    if rows and rows[0].get("event_type") != "RUN_START":
        errors.append("first event is not RUN_START")
    if rows and rows[-1].get("event_type") != "RUN_END":
        errors.append("last event is not RUN_END")
    model_requests = Counter()
    model_closures = Counter()
    tool_requests = Counter()
    tool_closures = Counter()
    for row in rows:
        if row.get("event_type") not in EVENT_TYPES:
            errors.append(f"unknown event type {row.get('event_type')}")
        payload = json.dumps(row, ensure_ascii=False)
        if SECRET_RE.search(payload):
            errors.append(f"possible credential in seq {row.get('seq')}")
        if PRIVATE_KEY_RE.search(payload):
            errors.append(f"private answer-key field in seq {row.get('seq')}")
        event_type = row.get("event_type")
        payload_obj = row.get("payload") or {}
        if event_type == "MODEL_REQUEST":
            model_requests[row.get("span_id")] += 1
        elif event_type in {"MODEL_RESPONSE", "MODEL_ERROR"}:
            parent = row.get("parent_span_id") or str(row.get("span_id", "")).rsplit(":", 1)[0]
            model_closures[parent] += 1
        elif event_type == "TOOL_CALL":
            tool_requests[row.get("span_id")] += 1
        elif event_type in {"TOOL_RESULT", "TOOL_ERROR"}:
            parent = row.get("parent_span_id") or str(row.get("span_id", "")).rsplit(":", 1)[0]
            tool_closures[parent] += 1
        if event_type == "MODEL_REQUEST" and not isinstance(payload_obj.get("messages"), list):
            errors.append(f"seq {row.get('seq')}: model request missing messages")
        if event_type == "TOOL_CALL" and not payload_obj.get("tool_name"):
            errors.append(f"seq {row.get('seq')}: tool call missing tool_name")
    for span, count in model_requests.items():
        if count != 1 or model_closures[span] != 1:
            errors.append(f"model span {span}: request={count}, closure={model_closures[span]}")
    for span, count in tool_requests.items():
        if count != 1 or tool_closures[span] != 1:
            errors.append(f"tool span {span}: request={count}, closure={tool_closures[span]}")
    return {"events": len(rows), "errors": errors, "event_counts": dict(Counter(row.get("event_type") for row in rows))}


def check_steps(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"steps read failed: {exc}"]
    previous_seq = 0
    for index, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"steps line {index}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict) or row.get("event_type") not in {"STEP_START", "STEP_END"}:
            errors.append(f"steps line {index}: not a STEP_START/STEP_END event")
            continue
        seq = int(row.get("seq", 0) or 0)
        if seq <= previous_seq:
            errors.append(f"steps line {index}: sequence is not increasing")
        previous_seq = seq
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    manifest = load(args.run_dir / "manifest.json")
    if not isinstance(manifest, dict):
        print(json.dumps({"status": "FAIL", "errors": ["missing or invalid run manifest"]}))
        return 2
    errors: list[str] = []
    if manifest.get("mode") != "answer_given_reverse_reasoning" or manifest.get("group") != "G5":
        errors.append("run is not isolated answer-given G5")
    if manifest.get("no_private_answer_access") is not True:
        errors.append("no_private_answer_access is not true")
    if manifest.get("answer_exposure") != "given_to_g5_only":
        errors.append("answer exposure contract mismatch")
    task_summaries = []
    for summary_path in sorted(args.run_dir.glob("models/*/tasks/*/summary.json")):
        summary = load(summary_path)
        if not isinstance(summary, dict):
            errors.append(f"invalid summary: {summary_path}")
            continue
        task_summaries.append(summary)
        if summary.get("no_private_answer_access") is not True:
            errors.append(f"private access flag failed: {summary_path}")
        attempt = int(summary.get("attempt", 0) or 0)
        attempt_dir = summary_path.parent / "attempts" / f"attempt-{attempt:03d}"
        event_path = attempt_dir / "events.jsonl"
        event_check = check_events(event_path)
        errors.extend(f"{summary_path}: {item}" for item in event_check["errors"])
        errors.extend(f"{summary_path}: {item}" for item in check_steps(attempt_dir / "steps.jsonl"))
        if not (attempt_dir / "manifest.json").is_file() or not (attempt_dir / "checkpoint.json").is_file() or not (attempt_dir / "proof_graph.json").is_file() or not (attempt_dir / "stderr.log").is_file():
            errors.append(f"missing durable artifacts: {summary_path}")
    expected_tasks = len(manifest.get("task_ids", [])) * len(manifest.get("models", []))
    counts = Counter(str(row.get("status")) for row in task_summaries)
    report = {
        "status": "PASS" if not errors and len(task_summaries) == expected_tasks else "FAIL",
        "run_dir": str(args.run_dir.resolve()),
        "expected_task_summaries": expected_tasks,
        "observed_task_summaries": len(task_summaries),
        "status_counts": dict(counts),
        "errors": errors[:200],
        "error_count": len(errors),
        "private_answer_key_read": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
