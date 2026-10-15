#!/usr/bin/env python3
"""Independent read-only integrity audit for the persisted G0--G8 artifacts.

This is an engineering/data-lineage audit. It does not decide scientific truth
and it deliberately reports unresolved external/math/statistical gates.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
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


def readl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def count_model_key_hits(paths: list[Path]) -> dict[str, int]:
    hits: collections.Counter[str] = collections.Counter()
    for path in paths:
        for row in readl(path):
            if row.get("event_type") != "MODEL_REQUEST":
                continue
            text = json.dumps(row.get("payload", {}), ensure_ascii=False)
            for key in FORBIDDEN_MODEL_KEYS:
                if key in text:
                    hits[key] += 1
    return dict(hits)


def count_nested_model_key_hits(paths: list[Path]) -> dict[str, int]:
    hits: collections.Counter[str] = collections.Counter()
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        events = ((data.get("response") or {}).get("events") or [])
        for event in events:
            if event.get("event_type") != "MODEL_REQUEST":
                continue
            text = json.dumps(event.get("payload", {}), ensure_ascii=False)
            for key in FORBIDDEN_MODEL_KEYS:
                if key in text:
                    hits[key] += 1
    return dict(hits)


def summarize_retry(root: Path, plan_name: str, states_name: str, q_name: str,
                    manifest_name: str, merge_name: str) -> dict[str, Any]:
    """Summarize one immutable retry directory from canonical files only."""
    plan = readl(root / plan_name)
    states = readl(root / states_name)
    q = readl(root / q_name)
    manifest_path = root / manifest_name
    merge_path = root / merge_name
    merge = json.loads(merge_path.read_text(encoding="utf-8")) if merge_path.is_file() else None
    state_merge = (merge or {}).get("states") or {}
    return {
        "root": str(root),
        "plan_rows": len(plan),
        "state_status_counts": dict(collections.Counter(row.get("status") for row in states)),
        "q_rows": len(q),
        "q_valid": sum(bool(row.get("is_valid")) for row in q),
        "retry_manifest": json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None,
        "merge_manifest": merge,
        "canonical_state_rows": state_merge.get("selected_records"),
        "canonical_expected_state_rows": state_merge.get("expected"),
        "canonical_missing_state_ids": state_merge.get("missing_ids", []),
        "canonical_state_complete": bool(state_merge) and not state_merge.get("missing_ids"),
        "forbidden_model_request_key_hits": count_model_key_hits(list(root.glob("**/events.jsonl"))),
        "key_hashes": {name: sha256(root / name) for name in [plan_name, states_name, q_name]},
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    g6 = root / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z"
    g7 = root / "results/g7_failure_localization/formal-20261014T030000Z-16workers"
    retry = root / "results/g7_failure_localization/formal-20261015T060000Z-terminal-retry"
    retry2 = root / "results/g7_failure_localization/formal-20261015T073000Z-terminal-retry2"
    retry3 = root / "results/g7_failure_localization/formal-20261015T080000Z-terminal-retry3"
    protocol = root / "results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers"
    g8 = root / "results/g8_causal_mechanism/formal-20261015T030000Z-16workers"

    issues = json.loads((root / "docs/state/issues.json").read_text(encoding="utf-8"))
    issue_counts = collections.Counter(row["status"] for row in issues["issues"])

    g6_plan = readl(g6 / "run_plan.jsonl")
    g6_responses = readl(g6 / "responses.jsonl")
    g6_handoff = readl(g6 / "g6_to_g7_handoff.jsonl")
    g7_plan = readl(g7 / "g7_run_plan.jsonl")
    g7_states = readl(g7 / "g7_states.jsonl")
    g7_checkpoints = readl(g7 / "g7_checkpoints.jsonl")
    g7_q = readl(g7 / "g7_q_audit.jsonl")
    retry_plan = readl(retry / "g7_retry_plan.jsonl")
    retry_states = readl(retry / "g7_retry_states.jsonl")
    retry_q = readl(retry / "g7_retry_q_audit.jsonl")
    g8_plan = readl(g8 / "g8_run_plan.jsonl")
    g8_audit = json.loads((g8 / "audit/g8_independent_audit.json").read_text(encoding="utf-8"))
    g8_summary = json.loads((g8 / "raw/execution_summary.json").read_text(encoding="utf-8"))

    g7_trace_files = list(g7.glob("**/events.jsonl"))
    g8_result_files = list((g8 / "raw").glob("g8_*/result.json"))
    edge_counts = collections.Counter()
    for row in readl(g7 / "g7_vlu_oracle_audit.json") if (g7 / "g7_vlu_oracle_audit.json").suffix == ".jsonl" else []:
        edge_counts[str(len((row.get("l") or {}).get("edges", [])))] += 1
    vlu = json.loads((g7 / "g7_vlu_oracle_audit.json").read_text(encoding="utf-8"))

    legacy_dirs = ["pilot", "engineering_validation", "final_smoke", "theory", "theory_agent_smoke"]
    legacy_inventory: dict[str, Any] = {}
    for name in legacy_dirs:
        files = list((root / "results" / name).rglob("*.json"))
        mock = 0
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("is_mock") is True or data.get("mock") is True:
                mock += 1
        legacy_inventory[name] = {"json_files": len(files), "mock_marked_files": mock}

    report = {
        "audit_version": "g0-g8-integrity-v1",
        "audit_scope": "read_only_lineage_and_protocol_checks; no_scientific_truth_decision",
        "review": {
            "status": "COMPLETED_WITH_EXTERNAL_REVIEW_CAVEATS",
            "confirmed_issue_ids": [
                "ISSUE-3d7a9c1e5b20",
                "ISSUE-1f8c2b6a4d90",
                "ISSUE-000000000002",
                "ISSUE-000000000003",
                "ISSUE-000000000004",
                "ISSUE-ff97c7c89112",
                "ISSUE-ad61f025976a",
                "ISSUE-f9171bb760b1",
            ],
            "resolutions": [],
            "note": "The audit confirms persisted facts and repairs only the G7 prompt metadata leak; it does not certify scientific truth, external billing, immutable weights, mathematical review, or causal conclusions.",
        },
        "issue_ledger_status_counts": dict(issue_counts),
        "g0_g5_inventory": legacy_inventory,
        "g6": {
            "root": str(g6),
            "plan_rows": len(g6_plan),
            "response_rows": len(g6_responses),
            "handoff_rows": len(g6_handoff),
            "worker_counts": sorted({json.loads(p.read_text(encoding="utf-8")).get("worker_count") for p in g6.glob("runner_manifest*.json")}),
            "key_hashes": {name: sha256(g6 / name) for name in ["run_plan.jsonl", "responses.jsonl", "g6_to_g7_handoff.jsonl"]},
            "release_review": json.loads((g6 / "g6_release_review_final.json").read_text(encoding="utf-8")),
        },
        "g7_original": {
            "plan_rows": len(g7_plan),
            "state_status_counts": dict(collections.Counter(row.get("status") for row in g7_states)),
            "checkpoint_status_counts": dict(collections.Counter(row.get("status") for row in g7_checkpoints)),
            "q_rows": len(g7_q),
            "q_valid": sum(bool(row.get("is_valid")) for row in g7_q),
            "trace_files": len(g7_trace_files),
            "forbidden_model_request_key_hits": count_model_key_hits(g7_trace_files),
            "vlu_audit": vlu,
            "key_hashes": {name: sha256(g7 / name) for name in ["g7_run_plan.jsonl", "g7_states.jsonl", "g7_checkpoints.jsonl", "g7_q_audit.jsonl"]},
        },
        "g7_terminal_retry": {
            "plan_rows": len(retry_plan),
            "state_status_counts": dict(collections.Counter(row.get("status") for row in retry_states)),
            "q_rows": len(retry_q),
            "q_valid": sum(bool(row.get("is_valid")) for row in retry_q),
            "retry_manifest": json.loads((retry / "retry_manifest.json").read_text(encoding="utf-8")),
            "merge_manifest": json.loads((retry / "g7_merge_manifest.json").read_text(encoding="utf-8")),
            "forbidden_model_request_key_hits": count_model_key_hits(list(retry.glob("**/events.jsonl"))),
        },
        "g7_terminal_retry_chain": [
            summarize_retry(retry, "g7_retry_plan.jsonl", "g7_retry_states.jsonl", "g7_retry_q_audit.jsonl",
                            "retry_manifest.json", "g7_merge_manifest.json"),
            summarize_retry(retry2, "g7_retry2_plan.jsonl", "g7_retry2_states.jsonl", "g7_retry2_q_audit.jsonl",
                            "retry2_manifest.json", "g7_merge_manifest.json"),
            summarize_retry(retry3, "g7_retry3_plan.jsonl", "g7_retry3_states.jsonl", "g7_retry3_q_audit.jsonl",
                            "retry3_manifest.json", "g7_merge_manifest.json"),
        ],
        "g7_protocol_corrected_retry": summarize_retry(
            protocol, "g7_full_retry_plan.jsonl", "g7_full_retry_states.jsonl", "g7_full_retry_q_audit.jsonl",
            "g7_full_retry_manifest.json", "g7_merge_manifest.json"),
        "g8": {
            "plan_rows": len(g8_plan),
            "result_files": len(g8_result_files),
            "execution_summary": g8_summary,
            "independent_audit": g8_audit,
            "forbidden_model_request_key_hits": count_nested_model_key_hits(g8_result_files),
            "key_hashes": {name: sha256(g8 / name) for name in ["g8_run_plan.jsonl", "g9_handoff.json"]},
        },
        "findings": [
            "G0-G5 persisted legacy artifacts are inventoried; they are not reclassified as new formal runs.",
            "G6 corrected release is complete structurally and remains subject to the ledger's external math/provider/statistical caveats.",
            "Original G7 terminal failures and low Q validity remain present; the retry is separate and is not pooled.",
            "G7 terminal retries 1-3 are separately canonicalized; terminal rows remain failures and no retry is pooled into the original run.",
            "The G7 runner protocol was repaired so cf_type and theory_family_id are no longer model-facing hints for future runs.",
            "The protocol-corrected G7 retry is separately canonicalized with 1288 plan rows, 184 checkpoints, and retained terminal provider failures.",
            "G8 independent audit retains all 324 planned rows and does not load private oracle or decide scientific truth.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
