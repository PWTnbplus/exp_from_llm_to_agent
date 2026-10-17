import json

from src.scientific_discovery.models.provider import MockLLMProvider
from scripts.run_g6_counterfactual import G6_FORMAT_RETRY_INSTRUCTION, Limits, run_one


def test_g6_invalid_format_gets_one_bounded_retry_and_completes(tmp_path) -> None:
    invalid = {"decision": "MAINTAIN", "affected_claim_ids": [], "revised_claim": None}
    valid = {
        "decision": "MAINTAIN",
        "affected_claim_ids": [],
        "revised_claim": None,
        "supporting_evidence": "public evidence",
    }
    provider = MockLLMProvider(responses=[invalid, valid, valid])
    case = {
        "case_id": "case-1",
        "cf_type": "CF1",
        "theory_family_id": "family-1",
        "model_visible": {"original_problem": "public"},
    }
    plan = {
        "run_id": "g6-run-1",
        "arm_id": "G6_B_G4_HIDDEN",
        "group_id": "G4",
    }

    result = run_one(case, plan, provider, Limits(8, 8, 100_000, 10.0), tmp_path)

    assert result["status"] == "completed"
    assert len(provider.calls) == 3
    assert provider.calls[1]["messages"][-1]["content"] == G6_FORMAT_RETRY_INSTRUCTION
    events = [json.loads(line) for line in (tmp_path / "traces" / "g6-run-1" / "events.jsonl").read_text().splitlines()]
    assert sum(event["event_type"] == "FORMAT_RETRY_SCHEDULED" for event in events) == 1


def test_g6_final_g3_pass_gets_one_bounded_format_retry(tmp_path) -> None:
    valid = {
        "decision": "MAINTAIN",
        "affected_claim_ids": [],
        "revised_claim": None,
        "supporting_evidence": "public evidence",
    }
    invalid = {"decision": "MAINTAIN", "affected_claim_ids": [], "revised_claim": None}
    provider = MockLLMProvider(responses=[valid, invalid, valid])
    case = {
        "case_id": "case-2",
        "cf_type": "CF1",
        "theory_family_id": "family-2",
        "model_visible": {"original_problem": "public"},
    }
    plan = {"run_id": "g6-run-2", "arm_id": "G6_A_G3_GIVEN", "group_id": "G3"}

    result = run_one(
        case, plan, provider, Limits(8, 8, 100_000, 10.0), tmp_path,
        protocol_profile="g6_protocol_g3_tools_iteration",
    )

    assert result["status"] == "completed"
    assert len(provider.calls) == 3
    events = [json.loads(line) for line in (tmp_path / "traces" / "g6-run-2" / "events.jsonl").read_text().splitlines()]
    assert sum(event["event_type"] == "FORMAT_RETRY_SCHEDULED" for event in events) == 1
