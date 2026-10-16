"""Regression tests for fail-closed G6/G7 input indexing."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _load("audit_g6_counterfactual_test", ROOT / "scripts" / "audit_g6_counterfactual.py")
handoff = _load("build_g6_g7_handoff_test", ROOT / "scripts" / "build_g6_g7_handoff.py")


def _plan() -> list[dict]:
    return [{"run_id": "r1", "case_id": "c1", "group_id": "G3", "cf_type": "CF1", "theory_family_id": "f1", "replicate": 0, "arm_id": "G3"}]


def _oracle() -> list[dict]:
    return [{"case_id": "c1", "expected_decision": "MAINTAIN", "affected_claim_ids": []}]


def _response() -> list[dict]:
    return [{"run_id": "r1", "decision": "MAINTAIN", "trace_ref": "traces/r1/events.jsonl", "affected_claim_ids": []}]


def test_g6_audit_index_reports_duplicate_ids_without_replacement() -> None:
    indexed, failures = audit.index_unique(_plan() + _plan(), "run_id", "plan_run_id")
    assert list(indexed) == ["r1"]
    assert failures == ["duplicate_plan_run_id:r1"]


def test_handoff_rejects_duplicate_response_before_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan = _plan()
    oracle = _oracle()
    responses = _response() + _response()
    for name, rows in (("plan", plan), ("oracle", oracle), ("responses", responses)):
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )
    out = tmp_path / "handoff.jsonl"
    monkeypatch.setattr(sys, "argv", [
        "build_g6_g7_handoff.py", "--plan", str(tmp_path / "plan.jsonl"),
        "--oracle", str(tmp_path / "oracle.jsonl"), "--responses", str(tmp_path / "responses.jsonl"),
        "--out", str(out),
    ])
    with pytest.raises(SystemExit, match="duplicate response run_id"):
        handoff.main()
    assert not out.exists()


def test_handoff_rejects_unexpected_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan = _plan()
    oracle = _oracle()
    responses = _response() + [{"run_id": "extra", "decision": "MAINTAIN"}]
    for name, rows in (("plan", plan), ("oracle", oracle), ("responses", responses)):
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )
    out = tmp_path / "handoff.jsonl"
    monkeypatch.setattr(sys, "argv", [
        "build_g6_g7_handoff.py", "--plan", str(tmp_path / "plan.jsonl"),
        "--oracle", str(tmp_path / "oracle.jsonl"), "--responses", str(tmp_path / "responses.jsonl"),
        "--out", str(out),
    ])
    with pytest.raises(SystemExit, match="unexpected responses"):
        handoff.main()
    assert not out.exists()
