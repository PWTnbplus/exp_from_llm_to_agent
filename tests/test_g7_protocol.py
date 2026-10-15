from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from src.scientific_discovery.models.provider import MockLLMProvider
from scripts.run_g7_failure_localization import (
    FORMAT_RETRY_INSTRUCTION,
    Limits,
    case_prompt,
    normalize_stages,
    parse_payload,
    persisted_usage,
    public_tool_loop,
    protocol_preflight,
)
import scripts.run_g7_failure_localization as g7_runner


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


def test_g7_runner_preflight_rejects_routing_metadata_before_provider_setup() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public", "cf_type": "CF1"}}],
        [{"case_id": "case-1"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1"}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["routing_metadata_in_model_prompt"]
    assert report["provider_calls_made"] is False


def test_g7_runner_preflight_rejects_nested_private_model_fields() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"public": {"Ground_Truth": "secret"}, "answer_key": "secret"}}],
        [{"case_id": "case-1"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1"}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["private_oracle_metadata_in_model_prompt"]
    assert report["forbidden_model_prompt_hits"]["ground_truth"] == 1
    assert report["forbidden_model_prompt_hits"]["answer_key"] == 1


def test_g7_runner_preflight_rejects_malformed_plan_rows() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1"}],
        [{"checkpoint_id": "cp-1", "case_id": "case-1"}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["plan_required_fields_missing"]
    assert report["counts"]["missing_required_plan_fields"] == ["run_id"]


def test_g7_runner_main_fails_closed_before_reading_provider_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    public = tmp_path / "public.jsonl"
    labels = tmp_path / "labels.jsonl"
    plan = tmp_path / "plan.jsonl"
    public.write_text(json.dumps({"case_id": "case-1", "model_visible": {"cf_type": "CF1"}}) + "\n", encoding="utf-8")
    labels.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    plan.write_text(json.dumps({"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1"}) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "run_g7_failure_localization.py", "--public", str(public), "--labels", str(labels),
        "--plan", str(plan), "--out", str(out), "--model-id", "unused",
        "--key-file", str(tmp_path / "missing-key"), "--allow-paid",
    ])
    with pytest.raises(SystemExit, match="protocol preflight failed"):
        g7_runner.main()
    report = json.loads((out / "g7_protocol_preflight.json").read_text(encoding="utf-8"))
    assert report["provider_calls_made"] is False
    assert "routing_metadata_in_model_prompt" in report["errors"]


def test_g7_malformed_stage_contract_is_retained_as_failure() -> None:
    with pytest.raises(ValueError, match="missing stage Q"):
        normalize_stages({"stages": {"V": {}, "L": {}, "U": {}}})


def test_g7_invalid_decision_is_not_silently_repaired() -> None:
    with pytest.raises(ValueError, match="invalid decision"):
        parse_payload('{"decision":"guess"}')


def test_g7_format_retry_is_bounded_and_audited(tmp_path: Path) -> None:
    valid = {
        "decision": "MAINTAIN",
        "affected_claim_ids": [],
        "revised_claim": "",
        "supporting_evidence": [],
        "stages": {
            "V": {"verdict": "SUPPORTED"},
            "L": {"nodes": [], "edges": []},
            "U": {"node_changes": []},
            "Q": {"verdict": "PASS", "reason": "format contract"},
        },
    }
    provider = MockLLMProvider(responses=[{"decision": "MAINTAIN"}, valid, valid])
    limits = Limits(10, 10, 100000, 10.0)
    event_path = tmp_path / "events.jsonl"
    payload, _ = public_tool_loop(provider, [{"role": "user", "content": "public"}], "G4", limits,
                                  event_path, "trace-1", 0, False)
    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
    assert payload["decision"] == "MAINTAIN"
    assert len(provider.calls) == 3
    assert any(event["event_type"] == "FORMAT_RETRY_SCHEDULED" for event in events)
    assert any(event["event_type"] == "MODEL_REQUEST" and event["payload"]["format_retry"] for event in events)
    assert "top-level stages field" in FORMAT_RETRY_INSTRUCTION
    assert "stages.Q" in FORMAT_RETRY_INSTRUCTION


def test_g7_persisted_budget_is_scoped_to_worker_trace_ids(tmp_path: Path) -> None:
    events = [
        {"run_id": "trace-a", "event_type": "MODEL_REQUEST", "payload": {"messages": []}},
        {"run_id": "trace-a", "event_type": "MODEL_RESPONSE",
         "payload": {"usage": {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.25}}},
        {"run_id": "trace-b", "event_type": "MODEL_REQUEST", "payload": {"messages": []}},
        {"run_id": "trace-b", "event_type": "MODEL_RESPONSE",
         "payload": {"usage": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 2.5}}},
    ]
    path = tmp_path / "traces" / "trace-a" / "events.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    usage = persisted_usage(tmp_path, 0.001, 0.003, 1024, {"trace-a"})
    assert usage["model_calls"] == 1
    assert usage["total_tokens"] == 15
    assert usage["cost_usd"] == 0.25
