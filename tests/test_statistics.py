import json
from dataclasses import replace
from pathlib import Path

import pytest

from scientific_discovery.cli import _validate_design_manifest, main
from scientific_discovery.benchmark.task_registry import enumerate_newtonbench_tasks, stratified_select
from scientific_discovery.experiment.recorder import ResultRecorder
from scientific_discovery.benchmark.base import RunResult
from scientific_discovery.evaluation.statistics import (
    clustered_paired_bootstrap_ci,
    law_family_key,
)


def test_law_family_key_clusters_newtonbench_variants_but_not_unknown_tasks():
    assert law_family_key("newtonbench:m0_gravity:easy:v1:vanilla_equation") == "m0_gravity"
    assert law_family_key("newtonbench:m0_gravity:hard:v2:vanilla_equation") == "m0_gravity"
    assert law_family_key("other:task") == "other:task"


def test_cluster_bootstrap_is_deterministic_and_uses_family_units():
    values = [("family-a", 1.0), ("family-a", 1.0), ("family-b", -1.0)]
    first = clustered_paired_bootstrap_ci(values, seed=7, repeats=500)
    second = clustered_paired_bootstrap_ci(values, seed=7, repeats=500)
    assert first == second
    assert first[0] <= first[1]


def test_statistical_plan_freezes_repeats_and_failure_denominator():
    plan = json.loads((Path(__file__).parents[1] / "configs" / "statistical_plan.json").read_text(encoding="utf-8"))
    assert plan["version"] == "statistical-plan-v1"
    assert plan["status"] == "FROZEN_BEFORE_FORMAL_PAID_EVALUATION"
    assert plan["repeats_per_task_per_arm"]["pilot"] == 5
    assert plan["repeats_per_task_per_arm"]["formal"] == 5
    assert plan["denominator"]["include_all_registered_task_runs"] is True
    assert plan["denominator"]["missing_arm_is_not_silently_dropped"] is True


def test_design_manifest_rejects_mutated_registry_metadata():
    upstream = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    tasks = stratified_select(enumerate_newtonbench_tasks(upstream, seed=42), 12, 42)
    first, second = tasks[:2]
    mutated = [
        replace(task, domain=second.domain if task.task_id == first.task_id else first.domain if task.task_id == second.task_id else task.domain)
        for task in tasks
    ]
    with pytest.raises(SystemExit, match="metadata"):
        _validate_design_manifest(mutated, "pilot", upstream)


def test_cli_analysis_requires_frozen_manifest(tmp_path: Path):
    output = tmp_path / "analysis"
    with pytest.raises(SystemExit, match="requires --manifest"):
        main(["analyze", "--input", str(tmp_path), "--output", str(output)])


def test_cli_analysis_joins_frozen_manifest_and_expected_repeats(tmp_path: Path):
    upstream = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    manifest = [task.__dict__ for task in stratified_select(enumerate_newtonbench_tasks(upstream, seed=42), 12, 42)]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    input_dir = tmp_path / "results"
    input_dir.mkdir()
    output = tmp_path / "analysis"
    assert main(["analyze", "--input", str(input_dir), "--output", str(output), "--manifest", str(manifest_path), "--design", "pilot"]) == 0
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["expected_task_runs"] == 12 * 5 * 2
    assert summary["missing_registered_runs"] == 12 * 5 * 2
    assert summary["paired"]["n_pairs"] == 12 * 5
    assert summary["paired"]["missing_arm_pairs"] == 12 * 5
    assert len(summary["by_domain"]) == 12


def test_cli_analysis_rejects_manifest_sha_mismatch(tmp_path: Path):
    upstream = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    manifest = [task.__dict__ for task in stratified_select(enumerate_newtonbench_tasks(upstream, seed=42), 12, 42)]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = {
        "task_id": manifest[0]["task_id"],
        "runner": "llm_only",
        "validation": {"validated_success": False},
        "metadata": {
            "replicate_index": 0,
            "manifest_sha256": "stale",
            "task": {"domain": manifest[0]["domain"], "difficulty": manifest[0]["law_complexity"]},
            "budget": {"used": {}},
        },
    }
    input_dir = tmp_path / "results"
    input_dir.mkdir()
    (input_dir / "stale.json").write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(SystemExit, match="manifest SHA mismatch"):
        main(["analyze", "--input", str(input_dir), "--output", str(tmp_path / "analysis"), "--manifest", str(manifest_path), "--design", "pilot"])


def test_replicate_result_paths_are_stable_and_overwrite_safe(tmp_path: Path):
    result = RunResult("llm_only", "task", "failed", {"error": "test"}, run_id="random", metadata={"replicate_index": 3})
    recorder = ResultRecorder(tmp_path)
    path = recorder.write(result, {"validated_success": False}, replicate_index=3)
    assert path.name == "llm_only_task__replicate-003.json"
    try:
        recorder.write(result, {"validated_success": False}, replicate_index=3)
    except FileExistsError:
        pass
    else:
        raise AssertionError("replicate results must not be overwritten")
