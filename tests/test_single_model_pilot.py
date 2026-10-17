import argparse
import json

import scripts.run_single_model_pilot as pilot


def _args(tmp_path):
    return argparse.Namespace(
        model="unit-model",
        manifest=pilot.ROOT / "task_manifest.json",
        output=tmp_path / "pilot",
        repeats=1,
        limit_tasks=1,
        max_experiments=2,
        provider="mock",
        allow_paid=False,
        max_cost_usd=1.0,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.003,
        max_output_tokens=512,
        timeout_seconds=60.0,
        provider_timeout_seconds=5.0,
        resume=False,
        max_parallel=2,
    )


def test_single_model_pilot_checkpoints_all_registered_rows(tmp_path):
    result = pilot.run_pilot(_args(tmp_path))
    assert result["status"] == "COMPLETED"
    assert result["expected_runs"] == 2
    assert result["registered_runs"] == 2
    assert result["task_failures"] == 0
    payload = json.loads((_args(tmp_path).output / "result.json").read_text(encoding="utf-8"))
    assert payload["scientific_release_allowed"] is False
    assert {row["runner"] for row in payload["rows"]} == {"llm_only", "agent"}


def test_single_model_pilot_retains_runner_failure(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("deliberate failure")

    monkeypatch.setattr(pilot, "run_one", fail)
    result = pilot.run_pilot(_args(tmp_path))
    assert result["status"] == "COMPLETED_WITH_TASK_FAILURES"
    assert result["registered_runs"] == 2
    assert result["task_failures"] == 2
    failures = list((_args(tmp_path).output).rglob("task_failure.json"))
    assert len(failures) == 2
    assert json.loads(failures[0].read_text(encoding="utf-8"))["error_type"] == "RuntimeError"


def test_reconcile_recovers_durable_task_result_without_duplicate(tmp_path):
    task_dir = tmp_path / "replicate-000" / "agent" / "000_task"
    task_dir.mkdir(parents=True)
    (task_dir / "single_agent_task__replicate-000.json").write_text(json.dumps({
        "runner": "single_agent",
        "task_id": "task-1",
        "status": "failed",
        "metadata": {"budget": {"limits": {"max_cost_usd": 0.5}}, "provider_trace": []},
        "validation": {"validated_success": False},
    }), encoding="utf-8")
    rows = pilot._reconcile_task_artifacts(tmp_path, [])
    assert len(rows) == 1
    assert rows[0]["runner"] == "agent"
    assert rows[0]["task_id"] == "task-1"
    assert rows[0]["reconciled_from_task_artifact"] is True
