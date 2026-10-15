#!/usr/bin/env python3
"""Read-only forensic audit of G7 provider failures and Q invalidity.

This report classifies persisted failure events and independent-Q failures. It
does not repair, pool, reinterpret, or make a scientific truth decision.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any


FORBIDDEN_MODEL_KEYS = (
    "expected_decision",
    "oracle_affected_claim_ids",
    "correct_revised_claim",
    "private_oracle",
    "g6_private_oracle",
)
ROUTING_METADATA_KEYS = ("cf_type", "theory_family_id")


def readl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def event_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("**/events.jsonl")):
        rows.extend(readl(path))
    return rows


def count_model_key_hits(events: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for event in events:
        if event.get("event_type") != "MODEL_REQUEST":
            continue
        payload = json.dumps(event.get("payload", {}), ensure_ascii=False)
        for key in keys:
            if key in payload:
                counts[key] += 1
    return dict(counts)


def summarize(root: Path, plan_name: str, states_name: str, checkpoints_name: str,
              q_name: str, merge_name: str) -> dict[str, Any]:
    plan = readl(root / plan_name)
    states = readl(root / states_name)
    checkpoints = readl(root / checkpoints_name)
    q_rows = readl(root / q_name)
    events = event_rows(root)
    errors = collections.Counter(
        str((event.get("payload") or {}).get("error", "unknown"))
        for event in events
        if event.get("event_type") == "ERROR"
    )
    q_failure_combinations = collections.Counter()
    q_reasons = collections.Counter()
    for row in q_rows:
        if row.get("is_valid"):
            continue
        if row.get("reason"):
            q_reasons[str(row["reason"])] += 1
        checks = row.get("checks")
        if isinstance(checks, dict):
            q_failure_combinations["+".join(sorted(str(k) for k, value in checks.items() if not value)) or "none"] += 1

    response_events = [event for event in events if event.get("event_type") == "MODEL_RESPONSE"]
    usage = {
        "model_calls": sum(event.get("event_type") == "MODEL_REQUEST" for event in events),
        "tool_calls": sum(event.get("event_type") == "TOOL_CALL" for event in events),
        "total_tokens": sum(
            int((event.get("payload") or {}).get("usage", {}).get("input_tokens", 0))
            + int((event.get("payload") or {}).get("usage", {}).get("output_tokens", 0))
            for event in response_events
        ),
        "observed_cost_usd": sum(
            float((event.get("payload") or {}).get("usage", {}).get("cost_usd", 0.0))
            for event in response_events
        ),
    }
    merge = json.loads((root / merge_name).read_text(encoding="utf-8")) if (root / merge_name).is_file() else {}
    state_merge = merge.get("states") or {}
    return {
        "root": str(root),
        "plan_rows": len(plan),
        "state_status_counts": dict(collections.Counter(str(row.get("status")) for row in states)),
        "checkpoint_status_counts": dict(collections.Counter(str(row.get("status")) for row in checkpoints)),
        "canonical_state_rows": state_merge.get("selected_records"),
        "canonical_expected_state_rows": state_merge.get("expected"),
        "canonical_missing_state_ids": state_merge.get("missing_ids", []),
        "error_messages": dict(errors),
        "q_rows": len(q_rows),
        "q_valid": sum(bool(row.get("is_valid")) for row in q_rows),
        "q_invalid_reason_counts": dict(q_reasons),
        "q_invalid_check_combinations": dict(q_failure_combinations),
        "resource_usage": usage,
        "forbidden_model_request_key_hits": count_model_key_hits(events, FORBIDDEN_MODEL_KEYS),
        "routing_metadata_model_request_hits": count_model_key_hits(events, ROUTING_METADATA_KEYS),
        "format_retry_scheduled_events": sum(event.get("event_type") == "FORMAT_RETRY_SCHEDULED" for event in events),
        "format_retry_model_requests": sum(
            event.get("event_type") == "MODEL_REQUEST" and bool((event.get("payload") or {}).get("format_retry"))
            for event in events
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    base = root / "results/g7_failure_localization"
    specs = [
        ("original", base / "formal-20261014T030000Z-16workers", "g7_run_plan.jsonl", "g7_states.jsonl", "g7_checkpoints.jsonl", "g7_q_audit.jsonl", "g7_merge_manifest.json"),
        ("retry1", base / "formal-20261015T060000Z-terminal-retry", "g7_retry_plan.jsonl", "g7_retry_states.jsonl", "g7_retry_checkpoints.jsonl", "g7_retry_q_audit.jsonl", "g7_merge_manifest.json"),
        ("retry2", base / "formal-20261015T073000Z-terminal-retry2", "g7_retry2_plan.jsonl", "g7_retry2_states.jsonl", "g7_retry2_checkpoints.jsonl", "g7_retry2_q_audit.jsonl", "g7_merge_manifest.json"),
        ("retry3", base / "formal-20261015T080000Z-terminal-retry3", "g7_retry3_plan.jsonl", "g7_retry3_states.jsonl", "g7_retry3_checkpoints.jsonl", "g7_retry3_q_audit.jsonl", "g7_merge_manifest.json"),
        ("protocol_corrected", base / "formal-20261015T060000Z-protocol-corrected-16workers", "g7_full_retry_plan.jsonl", "g7_full_retry_states.jsonl", "g7_full_retry_checkpoints.jsonl", "g7_full_retry_q_audit.jsonl", "g7_merge_manifest.json"),
    ]
    report = {
        "audit_version": "g7-failure-taxonomy-v1",
        "audit_scope": "read_only_provider_failure_and_q_invalidity_classification; no_scientific_truth_decision",
        "review": {
            "status": "COMPLETED_WITH_G7_PROTOCOL_CAVEAT",
            "confirmed_issue_ids": ["ISSUE-3d7a9c1e5b20", "ISSUE-0f2cb195c681"],
            "resolutions": [],
            "note": "The repaired runner has zero routing-metadata hits in all non-pooled retries, but the immutable original G7 run contains routing metadata in model requests and remains non-confirmatory for that gate.",
        },
        "runs": {name: summarize(path, plan, states, checkpoints, q, merge) for name, path, plan, states, checkpoints, q, merge in specs},
        "conclusion": {
            "provider_failures_are_retained": True,
            "q_invalidity_is_retained": True,
            "retries_are_not_pooled": True,
            "scientific_truth_decision_made": False,
            "interpretation_boundary": "Error strings and independent-Q checks describe persisted execution evidence; they do not establish why the provider produced malformed output beyond the recorded contract failure.",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
