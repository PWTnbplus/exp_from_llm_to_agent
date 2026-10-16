from __future__ import annotations

from scripts.review_g7_scientific_selection import (
    index_unique,
    validate_public_checkpoint_inputs,
)


def test_public_case_and_checkpoint_indexes_require_unique_identities() -> None:
    public = [{"case_id": "case-1"}, {"case_id": "case-1"}]
    checkpoints = [
        {"checkpoint_id": "cp-1", "case_id": "case-1", "group_id": "G3", "status": "completed"},
        {"checkpoint_id": "cp-2", "case_id": "case-1", "group_id": "G3", "status": "completed"},
    ]
    by_case, by_pair, errors = validate_public_checkpoint_inputs(public, checkpoints)
    assert by_case["case-1"]["case_id"] == "case-1"
    assert by_pair[("case-1", "G3")]["checkpoint_id"] == "cp-1"
    assert "public_case_duplicate_identity:'case-1'" in errors
    assert "checkpoint_pair_duplicate_identity:('case-1', 'G3')" in errors


def test_checkpoint_ids_and_completion_status_are_fail_closed() -> None:
    _, errors = index_unique(
        [
            {"checkpoint_id": "cp-1"},
            {"checkpoint_id": "cp-1"},
        ],
        ("checkpoint_id",),
        "checkpoint",
    )
    assert errors == ["checkpoint_duplicate_identity:'cp-1'"]
    _, _, errors = validate_public_checkpoint_inputs(
        [{"case_id": "case-1"}],
        [{"checkpoint_id": "cp-1", "case_id": "case-1", "group_id": "G3", "status": "provider_error"}],
    )
    assert "checkpoint_not_completed:1" in errors


def test_malformed_public_and_checkpoint_identity_is_reported() -> None:
    _, _, errors = validate_public_checkpoint_inputs(
        [{"case_id": ""}],
        [{"checkpoint_id": "cp-1", "case_id": "case-1", "group_id": "", "status": "completed"}],
    )
    assert "public_case_missing_identity:1" in errors
    assert "checkpoint_pair_missing_identity:1" in errors
