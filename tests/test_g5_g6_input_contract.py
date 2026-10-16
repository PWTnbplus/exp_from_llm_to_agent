"""Regression tests for G5/G6 task-index collision guards."""
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
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


prepare = _load("prepare_g6_counterfactual_test", ROOT / "scripts" / "prepare_g6_counterfactual.py")
verify = _load("verify_g5_g6_inputs_test", ROOT / "scripts" / "verify_g5_g6_inputs.py")


def test_prepare_public_index_rejects_duplicate_task_ids(tmp_path: Path) -> None:
    path = tmp_path / "public_tasks.json"
    path.write_text(
        json.dumps([
            {"task_id": "TC-L1-001", "given_parameters": {"k": 1}},
            {"task_id": "TC-L1-001", "given_parameters": {"k": 999}},
        ]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate public task task_id"):
        prepare.load_public(path)


def test_verify_public_index_rejects_duplicate_task_ids() -> None:
    with pytest.raises(SystemExit, match="duplicate public task task_id"):
        verify.index_unique(
            [{"task_id": "TC-L1-001"}, {"task_id": "TC-L1-001"}],
            "task_id",
            "public task",
        )


def test_verify_source_index_rejects_duplicate_task_ids() -> None:
    with pytest.raises(SystemExit, match="duplicate G6 source index task_id"):
        verify.index_unique(
            [{"task_id": "TC-L1-001"}, {"task_id": "TC-L1-001"}],
            "task_id",
            "G6 source index",
        )


def test_verify_main_rejects_duplicate_public_tasks_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public = tmp_path / "public_tasks.json"
    public.write_text(
        json.dumps([{"task_id": "TC-L1-001"}, {"task_id": "TC-L1-001"}]),
        encoding="utf-8",
    )
    g6_out = tmp_path / "g6"
    g6_out.mkdir()
    (g6_out / "G6_SOURCE_INDEX.json").write_text(
        json.dumps({"source_rows": [{"task_id": "TC-L1-001"}]}),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", [
        "verify_g5_g6_inputs.py", "--g6-out", str(g6_out),
        "--public-tasks", str(public), "--out", str(out),
    ])
    with pytest.raises(SystemExit, match="duplicate public task task_id"):
        verify.main()
    assert not out.exists()


def test_indices_reject_missing_or_non_object_rows() -> None:
    with pytest.raises(ValueError, match="row 0 must be an object"):
        prepare.index_unique(["not-an-object"], "task_id", "public task")
    with pytest.raises(SystemExit, match="missing or invalid task_id"):
        verify.index_unique([{}], "task_id", "public task")
