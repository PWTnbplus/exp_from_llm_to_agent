from __future__ import annotations

import json
import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_g0_g7_gate_attestation_is_complete_and_fail_closed() -> None:
    payload = json.loads((ROOT / "docs/state/gates.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["status"] == "BLOCKED_PENDING_EXTERNAL_REVIEW_AND_PROVIDER_FAILURES"
    assert payload["scientific_release_allowed"] is False
    assert set(payload["gates"]) == {f"G{i}" for i in range(8)}
    allowed_statuses = {"PASS", "FAIL", "NOT_TESTED", "BLOCKED"}
    for gate_id, gate in payload["gates"].items():
        assert gate_id in {f"G{i}" for i in range(8)}
        assert gate["status"] in allowed_statuses
        assert isinstance(gate["evidence"], list) and gate["evidence"]
        assert isinstance(gate["verification_command"], str) and gate["verification_command"]
        assert gate["scientific_release_allowed"] is False
    assert payload["gates"]["G0"]["status"] == "BLOCKED"
    assert payload["gates"]["G6"]["status"] == "BLOCKED"
    assert payload["gates"]["G7"]["status"] == "BLOCKED"


def test_gate_attestation_does_not_turn_mock_or_engineering_evidence_into_science() -> None:
    payload = json.loads((ROOT / "docs/state/gates.json").read_text(encoding="utf-8"))
    assert payload["mock_is_not_science_evidence"] is True
    assert all(gate["scientific_release_allowed"] is False for gate in payload["gates"].values())
    assert payload["gates"]["G1"]["scope"] == "engineering_protocol_only"
    assert payload["gates"]["G5"]["scope"] == "smoke_and_engineering_only"


def test_local_newtonbench_artifacts_are_pinned_without_claiming_remote_provenance() -> None:
    archive = ROOT / "third_party/NewtonBench.zip"
    license_path = ROOT / "third_party/NewtonBench/LICENSE"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == (
        "f69e409e9e9332530dee04ed5c3175c7bba1d083dea4ab02ebffe6733115246e"
    )
    assert hashlib.sha256(license_path.read_bytes()).hexdigest() == (
        "47158d3a1eb6cbebe82fab657c11d4959c453f4d803b103a132b4627b63719f0"
    )
    assert license_path.read_text(encoding="utf-8").startswith("MIT License")
    with zipfile.ZipFile(archive) as handle:
        assert "NewtonBench-main/LICENSE" in handle.namelist()
    payload = json.loads((ROOT / "docs/state/gates.json").read_text(encoding="utf-8"))
    assert payload["gates"]["G0"]["status"] == "BLOCKED"
