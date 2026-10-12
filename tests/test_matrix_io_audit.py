from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_and_complete_theory_matrix import inspect_run


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _make_run(tmp_path: Path, *, trace_path: str = "logs/run.jsonl") -> Path:
    run_dir = tmp_path / "run"
    model_dir = run_dir / "models" / "model-a"
    trace = model_dir / trace_path
    trace.parent.mkdir(parents=True, exist_ok=True)
    trace.write_text(json.dumps({"event_type": "RUN_END"}) + "\n", encoding="utf-8")
    _write_json(
        run_dir / "run_manifest.json",
        {"mode": "G2", "group": "G2", "tasks_per_model": 2, "models": [{"model_id": "model-a"}]},
    )
    _write_json(
        run_dir / "parallel_launcher_summary.json",
        {"results": [{"model_id": "model-a", "exit_code": 0}], "all_processes_exit_zero": True},
    )
    _write_json(
        tmp_path / "data" / "public_tasks.json",
        [{"task_id": "task-1"}, {"task_id": "task-2"}],
    )
    _write_json(
        model_dir / "G2__task-1__run.json",
        {
            "task_id": "task-1",
            "mode": "G2",
            "group": "G2",
            "status": "COMPLETED",
            "validation": {"status": "PASS"},
            "trace_path": trace_path,
        },
    )
    return run_dir


def test_metadata_repair_keeps_missing_task_explicit(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)

    report, ledger = inspect_run(run_dir, tmp_path / "data", write_derived=True)

    assert report["answer_key_read"] is False
    assert report["raw_results_modified"] is False
    assert report["synthetic_results_created"] is False
    assert report["derived_completion_ledger_complete"] is True
    assert report["all_model_raw_io_complete"] is False
    assert [row["state"] for row in ledger["rows"]] == ["RECORDED_RESULT", "MISSING_RAW_RESULT"]
    assert (run_dir / "matrix_io_integrity_report.json").is_file()
    assert (run_dir / "matrix_completion_ledger.json").is_file()


def test_trace_escape_is_reported_without_following_external_path(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path, trace_path="../outside.jsonl")

    report, _ = inspect_run(run_dir, tmp_path / "data", write_derived=False)

    model = report["models"][0]
    assert model["raw_io_complete"] is False
    assert any(item["error"] == "trace_path_escapes_model_directory" for item in model["trace_read_errors"])
