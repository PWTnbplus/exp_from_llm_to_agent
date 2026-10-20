from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.v10.machine_truth import certificate, replay_certificate


def test_v10_truth_certificate_and_independent_replay_agree() -> None:
    cases = [
        ("x+2", "increasing", "all_real"),
        ("x+2", "decreasing", "all_real"),
        ("x**2", "increasing", "x>=0"),
        ("3-2*x", "decreasing", "all_real"),
    ]
    for expression, relation, domain in cases:
        cert = certificate(expression, relation, domain)
        replay = replay_certificate(expression, relation, domain)
        assert cert["status"] == replay["status"]


def test_v10_artifact_contract_after_run() -> None:
    run_value = os.environ.get("V10_RUN_ROOT")
    audit_value = os.environ.get("V10_AUDIT_ROOT")
    if not run_value or not audit_value:
        pytest.skip("V10_RUN_ROOT/V10_AUDIT_ROOT are set by the completed experiment")
    run_root = Path(run_value)
    audit_root = Path(audit_value)
    prereg = json.loads((run_root / "preregistration.json").read_text(encoding="utf-8"))
    acceptance = json.loads((audit_root / "MACHINE_ACCEPTANCE.json").read_text(encoding="utf-8"))
    independent = json.loads((audit_root / "INDEPENDENT_READ_ONLY_AUDIT.json").read_text(encoding="utf-8"))
    assert prereg["model_id"] == "kimi-k2.5"
    assert prereg["only_model"] is True
    assert acceptance["unique_base_language_models"] == ["kimi-k2.5"]
    assert independent["audit_pass"] is True
    assert acceptance["machine_execution_accepted"] is True
