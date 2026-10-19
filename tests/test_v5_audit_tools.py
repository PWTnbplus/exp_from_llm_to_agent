from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.v5.build_v5_pack import (
    build_g7_views,
    cluster_bootstrap,
    review_boundary_row,
)


def test_v5_g6_boundary_review_requires_two_independent_paths() -> None:
    row = {
        "run_id": "run-1",
        "case_id": "case-1",
        "status": "PASS",
        "reason_code": "BOUNDARY_CONDITION_HANDLED",
        "evidence": "k=0 implies x is constant and strict decrease is not licensed",
    }
    reviewed = review_boundary_row(row)
    assert reviewed["verdict"] == "PROVEN_EQUIVALENT"
    assert reviewed["symbolic_path_pass"] is True
    assert reviewed["numeric_path_pass"] is True


def test_v5_g6_review_does_not_promote_unscorable_row() -> None:
    reviewed = review_boundary_row({"status": "NOT_SCORED", "reason_code": "CLAIM_UNPARSABLE"})
    assert reviewed["verdict"] == "INCONCLUSIVE_OR_NOT_SCORABLE"


def test_v5_cluster_bootstrap_resamples_families_not_rows() -> None:
    rows = [
        {"family": "a", "success": True}, {"family": "a", "success": False},
        {"family": "b", "success": False},
    ]
    first = cluster_bootstrap(rows, family_key="family", success_key="success", samples=100)
    second = cluster_bootstrap(rows, family_key="family", success_key="success", samples=100)
    assert first == second
    assert 0.0 <= first[0] <= first[1] <= 1.0


def test_v5_g7_views_keep_original_failure_and_new_attempt_separate(tmp_path: Path) -> None:
    historical = tmp_path / "historical.csv"
    with historical.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "state_id", "checkpoint_id", "all_attempt_ids", "last_eligible_attempt",
            "selected_result_status", "selected_trace_ref", "selected_trace_sha256", "trace_integrity",
        ])
        writer.writeheader()
        writer.writerow({"state_id": "s-1", "checkpoint_id": "cp-1", "all_attempt_ids": "['a-1']",
                         "last_eligible_attempt": "a-1", "selected_result_status": "completed",
                         "selected_trace_ref": "traces/s-1/events.jsonl", "selected_trace_sha256": "old-hash",
                         "trace_integrity": "False"})
    incidents = tmp_path / "incidents.jsonl"
    incidents.write_text(json.dumps({"run_id": "s-1", "classification": "GENUINE_FINAL_ATTEMPT_INCONSISTENCY"}) + "\n", encoding="utf-8")
    plan = tmp_path / "recovery.jsonl"
    plan.write_text(json.dumps({"run_id": "s-1", "prior_status": "completed", "category": "TRACE_RETRY"}) + "\n", encoding="utf-8")
    root = tmp_path / "run"
    trace = root / "traces" / "s-1" / "events.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_text(
        json.dumps({"event_type": "RUN_START", "ts_utc": "2026-01-01T00:00:00Z"}) + "\n" +
        json.dumps({"event_type": "RUN_END", "payload": {"status": "completed"}, "ts_utc": "2026-01-01T00:01:00Z"}) + "\n",
        encoding="utf-8",
    )
    states = tmp_path / "states.jsonl"
    states.write_text(json.dumps({"run_id": "s-1", "checkpoint_id": "cp-1", "status": "completed",
                                  "trace_ref": "traces/s-1/events.jsonl"}) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    summary = build_g7_views(historical_csv=historical, historical_incidents=incidents,
                             recovery_plan=plan, recovery_states=states, recovery_root=root, out=out)
    assert summary["historical_rows"] == 1
    assert summary["historical_genuine_lifecycle_failures_retained"] == 1
    assert summary["recovery_unique_attempts"] == 1
    frozen = [json.loads(x) for x in (out / "G7_FROZEN_ORIGINAL_FULL_LEDGER.jsonl").read_text(encoding="utf-8").splitlines()]
    recovery = [json.loads(x) for x in (out / "G7_APPEND_ONLY_RECOVERY_VIEW.jsonl").read_text(encoding="utf-8").splitlines()]
    assert frozen[0]["attempt_id"] != recovery[0]["attempt_id"]
    assert frozen[0]["original_defect_retained"] is True
    assert recovery[0]["parent_attempt_id"] == "a-1"
