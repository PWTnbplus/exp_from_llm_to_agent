from __future__ import annotations

from scripts.prepare_g8_inputs import select_complete_families


def _public() -> list[dict]:
    return [
        {"case_id": "fam-CF1", "theory_family_id": "fam", "cf_type": "CF1"},
        {"case_id": "fam-CF2", "theory_family_id": "fam", "cf_type": "CF2"},
    ]


def _checkpoints(status: str = "completed") -> list[dict]:
    return [
        {"checkpoint_id": f"{cf}-{group}", "case_id": f"fam-{cf}", "group_id": group, "status": status}
        for cf in ("CF1", "CF2")
        for group in ("G3", "G4")
    ]


def test_noncompleted_checkpoint_cannot_complete_g8_family() -> None:
    rows = _checkpoints()
    rows[-1]["status"] = "provider_error"
    selected, errors, excluded = select_complete_families(_public(), rows)
    assert selected == []
    assert errors == ["expected exactly two CF1/CF2 cases per complete family, got 0"]
    assert excluded == {"provider_error": 1}


def test_duplicate_checkpoint_pair_and_id_fail_closed() -> None:
    rows = _checkpoints()
    rows.append(dict(rows[0], checkpoint_id="cp-duplicate"))
    selected, errors, _ = select_complete_families(_public(), rows)
    assert selected == []
    assert "checkpoint_pair_duplicate_identity:('fam-CF1', 'G3')" in errors

    rows = _checkpoints()
    rows.append(dict(rows[1], case_id="fam-CF1", group_id="G5"))
    rows[-1]["checkpoint_id"] = rows[0]["checkpoint_id"]
    _, errors, _ = select_complete_families(_public(), rows)
    assert "checkpoint_duplicate_identity:'CF1-G3'" in errors


def test_duplicate_public_case_is_not_used_for_denominator() -> None:
    public = _public() + [dict(_public()[0], case_id="fam-CF1-duplicate")]
    selected, errors, _ = select_complete_families(public, _checkpoints())
    assert selected == []
    assert errors == ["expected exactly two CF1/CF2 cases per complete family, got 3"]


def test_cf3_cf4_rows_are_not_part_of_the_g8_main_denominator() -> None:
    public = _public() + [
        {"case_id": "fam-CF3", "theory_family_id": "fam", "cf_type": "CF3"},
    ]
    checkpoints = _checkpoints() + [
        {"checkpoint_id": "CF3-G3", "case_id": "fam-CF3", "group_id": "G3", "status": "completed"},
    ]
    selected, errors, _ = select_complete_families(public, checkpoints)
    assert errors == []
    assert [row["case_id"] for row in selected] == ["fam-CF1", "fam-CF2"]
