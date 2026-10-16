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
        {"run_id": "r-g3", "case_id": "c1", "theory_family_id": "f1", "cf_type": "CF1", "replicate": 0, "group_id": "G3"},
        {"run_id": "r-g4", "case_id": "c1", "theory_family_id": "f1", "cf_type": "CF1", "replicate": 0, "group_id": "G4"},
    ]


def _private() -> list[dict]:
    return [{"case_id": "c1", "expected_decision": "MAINTAIN"}]


def _responses() -> list[dict]:
    return [{"run_id": "r-g3", "decision": "MAINTAIN"}, {"run_id": "r-g4", "decision": "MAINTAIN"}]


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


def test_missing_and_unexpected_responses_are_rejected() -> None:
    with pytest.raises(SystemExit, match="missing matched response run_id"):
        analysis.validate_statistical_inputs(_plan(), _private(), _responses()[:1])
    with pytest.raises(SystemExit, match="unexpected response run_id"):
        analysis.validate_statistical_inputs(
            _plan(), _private(), _responses() + [{"run_id": "extra", "decision": "MAINTAIN"}]
        )


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
