"""Fail-closed input-contract tests for the preregistered G6 analysis."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze_g6_clustered.py"
spec = importlib.util.spec_from_file_location("analyze_g6_clustered_test", SCRIPT)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def _plan() -> list[dict]:
    return [
        {"run_id": "r-g3", "case_id": "c1", "paired_set_id": "p1", "theory_family_id": "f1", "cf_type": "CF1", "replicate": 0, "group_id": "G3"},
        {"run_id": "r-g4", "case_id": "c1", "paired_set_id": "p1", "theory_family_id": "f1", "cf_type": "CF1", "replicate": 0, "group_id": "G4"},
    ]


def _private() -> list[dict]:
    return [{"case_id": "c1", "cf_type": "CF1", "expected_decision": "MAINTAIN"}]


def _responses() -> list[dict]:
    return [
        {"run_id": "r-g3", "decision": "MAINTAIN", "status": "completed"},
        {"run_id": "r-g4", "decision": "MAINTAIN", "status": "completed"},
    ]


def test_duplicate_response_run_id_is_rejected() -> None:
    with pytest.raises(SystemExit, match="duplicate response run_id"):
        analysis.validate_statistical_inputs(
            _plan(), _private(), _responses() + [{"run_id": "r-g3", "decision": "REVISE"}]
        )


def test_duplicate_private_case_id_is_rejected() -> None:
    with pytest.raises(SystemExit, match="duplicate private case_id"):
        analysis.validate_statistical_inputs(_plan(), _private() + _private(), _responses())


def test_duplicate_plan_arm_key_is_rejected() -> None:
    duplicate = _plan() + [{**_plan()[0], "run_id": "r-g3-duplicate"}]
    with pytest.raises(SystemExit, match="duplicate plan family/CF/replicate/arm"):
        analysis.validate_statistical_inputs(duplicate, _private(), _responses())


@pytest.mark.parametrize(
    ("field", "g4_value"),
    [("case_id", "c2"), ("paired_set_id", "p2")],
)
def test_mismatched_g3_g4_task_lineage_is_rejected(field: str, g4_value: str) -> None:
    plan = _plan()
    plan[1][field] = g4_value
    private = _private() + ([{"case_id": "c2", "expected_decision": "MAINTAIN"}] if field == "case_id" else [])
    with pytest.raises(SystemExit, match="mismatched G3/G4 task lineage"):
        analysis.validate_statistical_inputs(plan, private, _responses())


def test_missing_response_status_is_rejected() -> None:
    responses = _responses()
    responses[0].pop("status")
    with pytest.raises(SystemExit, match="invalid response status"):
        analysis.validate_statistical_inputs(_plan(), _private(), responses)


def test_completed_response_requires_known_decision() -> None:
    responses = _responses()
    responses[0]["decision"] = "GUESS"
    with pytest.raises(SystemExit, match="invalid completed decision"):
        analysis.validate_statistical_inputs(_plan(), _private(), responses)


def test_failed_response_with_matching_decision_is_not_correct() -> None:
    response = {"run_id": "r-g3", "decision": "MAINTAIN", "status": "provider_error"}
    assert not analysis.response_matches_oracle(response, _private()[0])


@pytest.mark.parametrize("replicate", ["0", True])
def test_non_integer_replicate_is_rejected(replicate: object) -> None:
    plan = _plan()
    plan[0]["replicate"] = replicate
    with pytest.raises(SystemExit, match="invalid plan replicate"):
        analysis.validate_statistical_inputs(plan, _private(), _responses())


def test_private_cf_type_must_match_plan() -> None:
    private = [{"case_id": "c1", "cf_type": "CF2", "expected_decision": "MAINTAIN"}]
    with pytest.raises(SystemExit, match="private cf_type mismatch"):
        analysis.validate_statistical_inputs(_plan(), private, _responses())


def test_missing_and_unexpected_responses_are_rejected() -> None:
    with pytest.raises(SystemExit, match="missing matched response run_id"):
        analysis.validate_statistical_inputs(_plan(), _private(), _responses()[:1])
    with pytest.raises(SystemExit, match="unexpected response run_id"):
        analysis.validate_statistical_inputs(
            _plan(), _private(), _responses() + [{"run_id": "extra", "decision": "MAINTAIN"}]
        )


def test_formal_layout_rejects_missing_counterfactual_type() -> None:
    with pytest.raises(SystemExit, match="statistical layout CF types"):
        analysis.validate_statistical_inputs(
            _plan(), _private(), _responses(),
            expected_families=1,
            expected_cf_types={"CF1", "CF2"},
            expected_replicates={0},
            expected_groups={"G3", "G4"},
        )


def test_unexpected_private_case_is_rejected() -> None:
    with pytest.raises(SystemExit, match="unexpected private case_id"):
        analysis.validate_statistical_inputs(
            _plan(), _private() + [{"case_id": "extra", "cf_type": "CF1", "expected_decision": "MAINTAIN"}], _responses()
        )


def test_main_rejects_incomplete_formal_layout_before_writing_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, rows in (("plan", _plan()), ("private", _private()), ("responses", _responses())):
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "analyze_g6_clustered.py", "--plan", str(tmp_path / "plan.jsonl"),
        "--private", str(tmp_path / "private.jsonl"), "--responses", str(tmp_path / "responses.jsonl"),
        "--out", str(out),
    ])
    with pytest.raises(SystemExit, match="statistical layout family count"):
        analysis.main()
    assert not out.exists()


def test_main_rejects_duplicate_response_before_writing_analysis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan = _plan()
    private = _private()
    responses = _responses() + [{"run_id": "r-g3", "decision": "REVISE"}]
    for name, rows in (("plan", plan), ("private", private), ("responses", responses)):
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "analyze_g6_clustered.py", "--plan", str(tmp_path / "plan.jsonl"),
        "--private", str(tmp_path / "private.jsonl"), "--responses", str(tmp_path / "responses.jsonl"),
        "--out", str(out),
    ])
    with pytest.raises(SystemExit, match="duplicate response run_id"):
        analysis.main()
    assert not out.exists()
