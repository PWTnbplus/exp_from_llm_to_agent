from __future__ import annotations

import json
import hashlib
import subprocess
import sys


def _public_case(model_visible: dict) -> dict:
    return {
        "case_id": "case-1", "paired_set_id": "family-1", "source_task_id": "task-1",
        "theory_family_id": "family-1", "domain": "theoretical_biology", "cf_type": "CF1",
        "split": "final_test", "quantifier": "forall_allowed_parameters",
        "model_visible": model_visible, "source_g5_graph_sha256": "0" * 64,
        "verification_grade": "C",
    }


def _label(public: dict | None = None) -> dict:
    public = public or _public_case({"problem": "public"})
    public_hash = hashlib.sha256(
        json.dumps(public, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "case_id": "case-1", "v": {"verdict": "SUPPORTED"},
        "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
        "eligible_u": False, "verifier_ref": "ref", "source_public_case_sha256": public_hash,
        "verification_grade": "C", "verification_method": "test_rulebook",
        "independent_verified": True, "synthetic_demo": False,
    }


def _plan_row(run_id: str, arm: str, group: str, stages: list[str]) -> dict:
    return {
        "run_id": run_id, "checkpoint_id": "cp-1", "case_id": "case-1",
        "experiment_id": "g7_failure_localization",
        "group_id": group, "diagnostic_arm": arm, "inject_stages": stages,
        "paired_set_id": "family-1", "theory_family_id": "family-1", "cf_type": "CF1",
        "split": "final_test",
        "source_g6_arm_id": "G6_A_G3_GIVEN" if group == "G3" else "G6_B_G4_GIVEN",
        "source_run_id": "g6-run-1", "source_checkpoint_id": "g6-cp-1",
        "profile": "theory_benchmark", "protocol_version": "g7-test-v1",
        "retry_scope": "test", "retry_protocol": "separate_frozen_retry_not_pooled",
        "replicate": 0, "arm_eligible_for_diagnostic": True,
    }


def test_g7_preflight_blocks_routing_metadata_in_model_visible_prompt(tmp_path) -> None:
    public = tmp_path / "public.jsonl"
    labels = tmp_path / "labels.jsonl"
    plan = tmp_path / "plan.jsonl"
    out = tmp_path / "preflight.json"
    public_row = _public_case({"cf_type": "CF1"})
    public.write_text(
        json.dumps(public_row) + "\n",
        encoding="utf-8",
    )
    labels.write_text(json.dumps(_label(public_row)) + "\n", encoding="utf-8")
    plan.write_text(json.dumps(_plan_row("run-1", "V_ONLY", "G4", ["V"])) + "\n", encoding="utf-8")

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
    public_row = _public_case({"problem": "public"})
    public.write_text(json.dumps(public_row) + "\n", encoding="utf-8")
    label_row = _label(public_row)
    label_row["eligible_u"] = True
    labels.write_text(json.dumps(label_row) + "\n", encoding="utf-8")
    arm_specs = [
        (arm, group, stages)
        for group in ("G3", "G4")
        for arm, stages in [
            ("D0", []), ("D1", ["V"]), ("D2", ["V", "L"]),
            ("D3", ["V", "L", "U"]), ("L_ONLY", ["L"]),
            ("U_ONLY", ["U"]), ("V_ONLY", ["V"]),
        ]
    ]
    plan.write_text(
        "\n".join(json.dumps(_plan_row(f"run-{group}-{arm}", arm, group, stages))
                  for arm, group, stages in arm_specs) + "\n",
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
