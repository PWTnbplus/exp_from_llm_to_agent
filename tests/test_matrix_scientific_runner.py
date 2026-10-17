import argparse
import json

import pytest

import scripts.run_matrix_scientific as adapter


def _args(tmp_path, mode="llm_only", provider="mock"):
    return argparse.Namespace(
        mode=mode,
        model="unit-model",
        output=tmp_path / mode,
        manifest=adapter.ROOT / "task_manifest.json",
        max_experiments=2,
        provider=provider,
        allow_paid=True,
        max_cost_usd=1.0,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.003,
        max_output_tokens=512,
        limit_tasks=1,
        timeout_seconds=60.0,
        provider_timeout_seconds=5.0,
    )


@pytest.mark.parametrize("mode", ["llm_only", "agent"])
def test_mock_adapter_emits_matrix_contract(tmp_path, mode):
    result = adapter.run_matrix_arm(_args(tmp_path, mode=mode))
    assert result["status"] == "COMPLETED"
    assert result["runner"] == mode
    assert result["mock"] is True
    assert result["protocol_valid"] is True
    assert result["budget_enforced"] is True
    assert (tmp_path / mode / "result.json").is_file()


def test_adapter_retains_task_failure_and_fails_closed(tmp_path, monkeypatch):
    def fail_run_one(*args, **kwargs):
        raise RuntimeError("deliberate adapter test failure")

    monkeypatch.setattr(adapter, "run_one", fail_run_one)
    result = adapter.run_matrix_arm(_args(tmp_path))
    assert result["status"] == "FAILED"
    assert result["task_failures"] == 1
    assert result["protocol_valid"] is False
    failure = next((tmp_path / "llm_only" / "tasks").glob("*/task_failure.json"))
    payload = json.loads(failure.read_text(encoding="utf-8"))
    assert payload["error_type"] == "RuntimeError"
    assert "deliberate adapter test failure" in payload["error_message"]


def test_manifest_rejects_duplicate_task_ids(tmp_path):
    source = json.loads((adapter.ROOT / "task_manifest.json").read_text(encoding="utf-8"))
    manifest = tmp_path / "duplicate.json"
    manifest.write_text(json.dumps([source[0], source[0]]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        adapter.load_tasks(manifest)
