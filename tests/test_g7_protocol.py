from __future__ import annotations

import json

import pytest

from scripts.run_g7_failure_localization import case_prompt, normalize_stages, parse_payload


def test_g7_case_prompt_keeps_stratification_metadata_out_of_model_text() -> None:
    prompt = case_prompt(
        {
            "case_id": "case-1",
            "cf_type": "CF1",
            "theory_family_id": "family-1",
            "model_visible": {"problem": "public"},
        }
    )
    payload = json.loads(prompt)
    assert payload == {"g7_public_case": {"problem": "public"}, "case_id": "case-1"}
    assert "cf_type" not in prompt
    assert "theory_family_id" not in prompt


def test_g7_malformed_stage_contract_is_retained_as_failure() -> None:
    with pytest.raises(ValueError, match="missing stage Q"):
        normalize_stages({"stages": {"V": {}, "L": {}, "U": {}}})


def test_g7_invalid_decision_is_not_silently_repaired() -> None:
    with pytest.raises(ValueError, match="invalid decision"):
        parse_payload('{"decision":"guess"}')
