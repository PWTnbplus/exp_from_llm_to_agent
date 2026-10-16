"""Fail-closed identity checks for the source-only G7 to G8 handoff."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "review_g7_g8_handoff_test", ROOT / "scripts" / "review_g7_g8_handoff.py"
)
handoff = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(handoff)


def test_duplicate_public_case_id_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate public case_id"):
        handoff.index_unique(
            [{"case_id": "case-1"}, {"case_id": "case-1"}],
            lambda row: row["case_id"],
            "public case_id",
        )


def test_duplicate_checkpoint_case_group_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate checkpoint case/group"):
        handoff.index_unique(
            [
                {"case_id": "case-1", "group_id": "G3"},
                {"case_id": "case-1", "group_id": "G3"},
            ],
            lambda row: (row["case_id"], row["group_id"]),
            "checkpoint case/group",
        )


def test_duplicate_checkpoint_id_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate checkpoint_id"):
        handoff.index_unique(
            [
                {"checkpoint_id": "cp-1"},
                {"checkpoint_id": "cp-1"},
            ],
            lambda row: row["checkpoint_id"],
            "checkpoint_id",
        )
