#!/usr/bin/env python3
"""Build a non-confirmatory, all-planned diagnostic report for corrected G7.

The scorer is read-only and keeps the planned denominator intact.  It may read
the private expected-decision file in the scoring process, but persists only
aggregate metrics and hashes; raw oracle values are never copied to the report.
Any formal preflight error, terminal failure, invalid Q row, or ineligible U
arm makes the report explicitly non-confirmatory.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any


DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}
PAIR_DEFINITIONS = (
    ("D0", "D1"),
    ("D1", "D2"),
    ("D2", "D3"),
    ("U_ONLY", "D0"),
    ("V_ONLY", "D0"),
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def first_error(q_row: dict[str, Any] | None, state: dict[str, Any]) -> str:
    if state.get("status") != "completed":
        return "MISSING_OR_TERMINAL_FAILURE"
    checks = q_row.get("checks") if isinstance(q_row, dict) else None
    if not isinstance(checks, dict):
        return "Q_AUDIT_MISSING"
    for key, name in (("V", "V"), ("L", "L"), ("U", "U"),
                      ("Q", "Q"), ("final_decision", "FINAL_DECISION")):
        if checks.get(key) is not True:
            return name
    return "NONE"


def _arm_key(row: dict[str, Any]) -> str:
    return f"{row.get('group_id')}__{row.get('diagnostic_arm')}"


def _expected_decisions(oracle_rows: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(row["case_id"]): str(row["expected_decision"]).upper()
        for row in oracle_rows
        if isinstance(row.get("case_id"), str)
        and str(row.get("expected_decision", "")).upper() in DECISIONS
    }


def _arm_metrics(rows: list[dict[str, Any]], states: dict[str, dict[str, Any]],
                 q_rows: dict[str, dict[str, Any]], expected: dict[str, str]) -> dict[str, Any]:
    planned = len(rows)
    completed = 0
    valid_answer = 0
    correct = 0
    w_to_c = 0
    c_to_w = 0
    q_valid = 0
    first_errors: collections.Counter[str] = collections.Counter()
    for plan in rows:
        run_id = str(plan.get("run_id"))
        state = states.get(run_id, {})
        q_row = q_rows.get(run_id)
        if q_row and q_row.get("is_valid") is True:
            q_valid += 1
        first_errors[first_error(q_row, state)] += 1
        if state.get("status") != "completed":
            continue
        completed += 1
        observed = str(state.get("final_decision", "")).upper()
        target = expected.get(str(plan.get("case_id")))
        if observed not in DECISIONS or target not in DECISIONS:
            continue
        valid_answer += 1
        is_correct = observed == target
        correct += int(is_correct)
        initial = str(state.get("initial_decision", "")).upper()
        if initial in DECISIONS:
            initial_correct = initial == target
            if not initial_correct and is_correct:
                w_to_c += 1
            if initial_correct and not is_correct:
                c_to_w += 1
    return {
        "planned": planned,
        "completed": completed,
        "completion_rate": ratio(completed, planned),
        "valid_answer_rows": valid_answer,
        "missing_or_invalid": planned - valid_answer,
        "all_planned_correct": correct,
        "all_planned_accuracy": ratio(correct, planned),
        "valid_only_accuracy": ratio(correct, valid_answer),
        "W_to_C": w_to_c,
        "C_to_W": c_to_w,
        "q_rows": sum(str(row.get("run_id")) in q_rows for row in rows),
        "q_valid": q_valid,
        "first_observable_error": dict(sorted(first_errors.items())),
    }


def _paired_metrics(plan_by_checkpoint: dict[tuple[str, str], dict[str, dict[str, Any]]],
                    states: dict[str, dict[str, Any]], expected: dict[str, str],
                    left: str, right: str, *, u_ineligible: bool,
                    preflight_errors: list[str]) -> dict[str, Any]:
    pairs = []
    for (group, checkpoint), arms in sorted(plan_by_checkpoint.items()):
        if left not in arms or right not in arms:
            continue
        l_plan, r_plan = arms[left], arms[right]
        l_state, r_state = states.get(str(l_plan["run_id"]), {}), states.get(str(r_plan["run_id"]), {})
        pairs.append({
            "left_completed": l_state.get("status") == "completed",
            "right_completed": r_state.get("status") == "completed",
            "left_correct": (
                l_state.get("status") == "completed"
                and str(l_state.get("final_decision", "")).upper() == expected.get(str(l_plan.get("case_id")))
            ),
            "right_correct": (
                r_state.get("status") == "completed"
                and str(r_state.get("final_decision", "")).upper() == expected.get(str(r_plan.get("case_id")))
            ),
        })
    both_completed = [row for row in pairs if row["left_completed"] and row["right_completed"]]
    status = "DIAGNOSTIC_ONLY"
    reason = "formal confirmatory score not authorized"
    if u_ineligible and ("U_ONLY" in {left, right} or left == "D3" or right == "D3"):
        status = "NOT_COMPUTABLE_INELIGIBLE_U"
        reason = "one paired arm requires a non-final U state, but no eligible U labels exist"
    elif preflight_errors:
        status = "NON_CONFIRMATORY_PREFLIGHT_FAILURE"
        reason = "formal preflight has errors"
    return {
        "left_arm": left,
        "right_arm": right,
        "status": status,
        "reason": reason,
        "planned_matched_checkpoints": len(pairs),
        "both_completed": len(both_completed),
        "left_correct_on_both_completed": sum(row["left_correct"] for row in both_completed),
        "right_correct_on_both_completed": sum(row["right_correct"] for row in both_completed),
    }


def build_report(*, plan_rows: list[dict[str, Any]], state_rows: list[dict[str, Any]],
                 q_rows: list[dict[str, Any]], oracle_rows: list[dict[str, Any]],
                 preflight: dict[str, Any], input_hashes: dict[str, str]) -> dict[str, Any]:
    states = {str(row.get("run_id")): row for row in state_rows}
    q_by_id = {str(row.get("run_id")): row for row in q_rows}
    expected = _expected_decisions(oracle_rows)
    by_arm: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    by_checkpoint: dict[tuple[str, str], dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    for row in plan_rows:
        by_arm[_arm_key(row)].append(row)
        by_checkpoint[(str(row.get("group_id")), str(row.get("checkpoint_id")))][str(row.get("diagnostic_arm"))] = row
    preflight_errors = [str(error) for error in preflight.get("errors", [])]
    counts = preflight.get("counts") or {}
    u_ineligible = bool(counts.get("ineligible_u_diagnostic_rows"))
    terminal_failures = sum(row.get("status") != "completed" for row in state_rows)
    invalid_q = sum(row.get("is_valid") is not True for row in q_rows)
    arm_metrics = {
        arm: _arm_metrics(rows, states, q_by_id, expected)
        for arm, rows in sorted(by_arm.items())
    }
    paired = {
        f"{group}:{left}_minus_{right}": _paired_metrics(
            by_checkpoint, states, expected, left, right,
            u_ineligible=u_ineligible, preflight_errors=preflight_errors,
        )
        for group in sorted({str(row.get("group_id")) for row in plan_rows})
        for left, right in PAIR_DEFINITIONS
    }
    confirmatory_allowed = not (
        preflight_errors or terminal_failures or invalid_q
        or u_ineligible or len(states) != len(plan_rows) or len(q_rows) != len(plan_rows)
    )
    return {
        "audit_version": "g7-corrected-metrics-v1",
        "audit_scope": "read_only_non_confirmatory_all_planned_diagnostic_metrics",
        "denominator_policy": "all planned rows; terminal failures and invalid Q rows remain in every planned denominator",
        "scientific_truth_decision_made": False,
        "confirmatory_reuse_allowed": confirmatory_allowed,
        "pooling_used": False,
        "inputs": input_hashes,
        "counts": {
            "plan_rows": len(plan_rows),
            "state_rows": len(state_rows),
            "q_rows": len(q_rows),
            "oracle_rows_scored": len(expected),
            "terminal_failures": terminal_failures,
            "invalid_q_rows": invalid_q,
            "preflight_errors": preflight_errors,
            "ineligible_u_rows": len(counts.get("ineligible_u_diagnostic_rows", [])),
        },
        "by_arm": arm_metrics,
        "paired_diagnostic_status": paired,
        "limitations": [
            "This report is not a formal result and cannot support mechanism, superiority, causal, or L/U claims.",
            "Q-invalid, terminal, and ineligible-U rows are not silently repaired or removed.",
            "Private oracle values are used only to derive aggregate correctness counts and are not persisted.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--q", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        plan_rows=readl(args.plan), state_rows=readl(args.states), q_rows=readl(args.q),
        oracle_rows=readl(args.oracle), preflight=json.loads(args.preflight.read_text(encoding="utf-8")),
        input_hashes={name: sha256(path) for name, path in (
            ("plan", args.plan), ("states", args.states), ("q", args.q),
            ("oracle", args.oracle), ("preflight", args.preflight),
        )},
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audit_version": report["audit_version"], "confirmatory_reuse_allowed": report["confirmatory_reuse_allowed"], "counts": report["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
