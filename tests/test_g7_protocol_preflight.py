from __future__ import annotations

import json
import subprocess
import sys


def test_g7_preflight_blocks_routing_metadata_in_model_visible_prompt(tmp_path) -> None:
    public = tmp_path / "public.jsonl"
    labels = tmp_path / "labels.jsonl"
    plan = tmp_path / "plan.jsonl"
    out = tmp_path / "preflight.json"
    public.write_text(
        json.dumps({"case_id": "case-1", "model_visible": {"cf_type": "CF1"}}) + "\n",
        encoding="utf-8",
    )
    labels.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    plan.write_text(json.dumps({"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1"}) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/g7_protocol_preflight.py",
            "--public",
            str(public),
            "--labels",
            str(labels),
            "--plan",
            str(plan),
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    report = json.loads(out.read_text(encoding="utf-8"))
    assert result.returncode == 2
    assert report["formal_run_allowed_by_protocol"] is False
    assert "routing_metadata_in_model_prompt" in report["errors"]


def test_g7_preflight_allows_shared_checkpoint_for_diagnostic_forks(tmp_path) -> None:
    public = tmp_path / "public.jsonl"
    labels = tmp_path / "labels.jsonl"
    plan = tmp_path / "plan.jsonl"
    out = tmp_path / "preflight.json"
    public.write_text(json.dumps({"case_id": "case-1", "model_visible": {"problem": "public"}}) + "\n", encoding="utf-8")
    labels.write_text(json.dumps({"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
                                  "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
                                  "eligible_u": False, "verifier_ref": "ref"}) + "\n", encoding="utf-8")
    plan.write_text(
        json.dumps({"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
                    "group_id": "G4", "diagnostic_arm": "V_ONLY", "inject_stages": ["V"]}) + "\n"
        + json.dumps({"run_id": "run-2", "checkpoint_id": "cp-1", "case_id": "case-1",
                      "group_id": "G4", "diagnostic_arm": "V_ONLY", "inject_stages": ["V"]}) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/g7_protocol_preflight.py",
            "--public",
            str(public),
            "--labels",
            str(labels),
            "--plan",
            str(plan),
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    report = json.loads(out.read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert report["formal_run_allowed_by_protocol"] is True
    assert report["counts"]["unique_checkpoint_ids"] == 1
