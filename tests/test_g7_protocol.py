from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys

import pytest

from src.scientific_discovery.models.provider import MockLLMProvider
from scripts.run_g7_failure_localization import (
    FORMAT_RETRY_INSTRUCTION,
    Limits,
    case_prompt,
    effective_worker_cost_cap,
    injection_for,
    model_visible_diagnostic_information,
    normalize_stages,
    parse_payload,
    persisted_usage,
    public_tool_loop,
    protocol_preflight,
    validate_paid_evidence,
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
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": "G4", "diagnostic_arm": "V_ONLY", "inject_stages": ["V"]}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["routing_metadata_in_model_prompt"]
    assert report["provider_calls_made"] is False


def test_g7_runner_preflight_rejects_nested_private_model_fields() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"public": {"Ground_Truth": "secret"}, "answer_key": "secret"}}],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": "G4", "diagnostic_arm": "V_ONLY", "inject_stages": ["V"]}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["private_oracle_metadata_in_model_prompt"]
    assert report["forbidden_model_prompt_hits"]["ground_truth"] == 1
    assert report["forbidden_model_prompt_hits"]["answer_key"] == 1


def test_g7_runner_preflight_rejects_malformed_plan_rows() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"checkpoint_id": "cp-1", "case_id": "case-1", "group_id": "G4",
          "diagnostic_arm": "V_ONLY", "inject_stages": ["V"]}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["plan_required_fields_missing"]
    assert report["counts"]["missing_required_plan_fields"] == ["run_id"]


def test_g7_runner_preflight_rejects_invalid_private_label_contract() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1", "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": "G4", "diagnostic_arm": "V_ONLY", "inject_stages": ["V"]}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["invalid_label_contract"]
    assert report["counts"]["invalid_label_cases"] == ["case-1"]


def test_g7_runner_preflight_rejects_invalid_plan_contract() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": {"bad": True}, "diagnostic_arm": "V_ONLY", "inject_stages": [{"bad": True}]}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["invalid_plan_contract"]
    assert report["counts"]["invalid_plan_rows"] == ["run-1"]


def test_g7_runner_preflight_rejects_unhashable_identifiers_without_crashing() -> None:
    report = protocol_preflight(
        [{"case_id": {"bad": True}, "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": {"bad": True}, "checkpoint_id": ["cp-1"], "case_id": {"bad": True},
          "group_id": "G4", "diagnostic_arm": "V_ONLY", "inject_stages": ["V"]}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert "invalid_public_case_ids" in report["errors"]
    assert "invalid_plan_contract" in report["errors"]


def test_g7_runner_preflight_rejects_arm_stage_mismatch() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": "G4", "diagnostic_arm": "D1", "inject_stages": ["L"]}],
        worker_count=1,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["invalid_plan_contract"]
    assert report["counts"]["invalid_plan_rows"] == ["run-1"]


def test_g7_formal_preflight_requires_all_diagnostic_arms_per_checkpoint() -> None:
    public = {"case_id": "case-1", "paired_set_id": "family-1", "source_task_id": "task-1",
              "theory_family_id": "family-1", "domain": "theoretical_biology", "cf_type": "CF1",
              "split": "final_test", "quantifier": "forall_allowed_parameters",
              "model_visible": {"problem": "public"}, "source_g5_graph_sha256": "0" * 64,
              "verification_grade": "C"}
    public_hash = hashlib.sha256(json.dumps(public, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    report = protocol_preflight(
        [public],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref", "source_public_case_sha256": public_hash,
          "verification_grade": "C", "verification_method": "test_rulebook",
          "independent_verified": True, "synthetic_demo": False}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": "G4", "diagnostic_arm": "D0", "inject_stages": [],
          "paired_set_id": "family-1", "theory_family_id": "family-1", "cf_type": "CF1",
          "split": "final_test", "source_g6_arm_id": "G6_B_G4_GIVEN",
          "source_run_id": "g6-run-1", "source_checkpoint_id": "g6-cp-1",
          "profile": "theory_benchmark", "protocol_version": "g7-test-v1",
          "retry_scope": "test", "retry_protocol": "separate_frozen_retry_not_pooled",
          "replicate": 0, "arm_eligible_for_diagnostic": True}],
        worker_count=1,
        require_complete_plan=True,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert report["errors"] == ["incomplete_arm_coverage"]
    assert report["counts"]["incomplete_arm_checkpoints"] == ["cp-1"]


def test_g7_formal_preflight_requires_design_metadata_contract() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": "G4", "diagnostic_arm": "D0", "inject_stages": []}],
        worker_count=1,
        require_complete_plan=True,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert "invalid_g7_public_metadata" in report["errors"]
    assert "invalid_g7_label_metadata" in report["errors"]
    assert "invalid_g7_plan_metadata" in report["errors"]


def test_g7_formal_preflight_rejects_public_plan_and_label_hash_mismatch() -> None:
    public = {"case_id": "case-1", "paired_set_id": "family-1", "source_task_id": "task-1",
              "theory_family_id": "family-1", "domain": "theoretical_biology", "cf_type": "CF1",
              "split": "final_test", "quantifier": "forall_allowed_parameters",
              "model_visible": {"problem": "public"}, "source_g5_graph_sha256": "0" * 64,
              "verification_grade": "C"}
    label = {"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
             "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
             "eligible_u": False, "verifier_ref": "ref", "source_public_case_sha256": "1" * 64,
             "verification_grade": "C", "verification_method": "test_rulebook",
             "independent_verified": True, "synthetic_demo": False}
    plan = {"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
            "group_id": "G4", "diagnostic_arm": "D0", "inject_stages": [],
            "paired_set_id": "family-1", "theory_family_id": "family-1", "cf_type": "CF2",
            "split": "final_test", "source_g6_arm_id": "G6_B_G4_GIVEN",
            "source_run_id": "g6-run-1", "source_checkpoint_id": "g6-cp-1",
            "profile": "theory_benchmark", "protocol_version": "g7-test-v1",
            "retry_scope": "test", "retry_protocol": "separate_frozen_retry_not_pooled",
            "replicate": 0, "arm_eligible_for_diagnostic": True}
    report = protocol_preflight([public], [label], [plan], worker_count=1, require_complete_plan=True)
    assert report["formal_run_allowed_by_protocol"] is False
    assert "g7_plan_public_mapping_mismatch" in report["errors"]
    assert "g7_label_public_hash_mismatch" in report["errors"]


def test_g7_formal_preflight_rejects_ineligible_u_diagnostic_arm() -> None:
    report = protocol_preflight(
        [{"case_id": "case-1", "model_visible": {"problem": "public"}}],
        [{"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
          "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
          "eligible_u": False, "verifier_ref": "ref"}],
        [{"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
          "group_id": "G4", "diagnostic_arm": "U_ONLY", "inject_stages": ["U"]}],
        worker_count=1,
        require_complete_plan=True,
    )
    assert report["formal_run_allowed_by_protocol"] is False
    assert "ineligible_u_diagnostic_arm" in report["errors"]
    assert report["counts"]["ineligible_u_diagnostic_rows"] == ["run-1"]


def test_g7_formal_preflight_rejects_plan_label_eligibility_mismatch() -> None:
    public = {"case_id": "case-1", "paired_set_id": "family-1", "source_task_id": "task-1",
              "theory_family_id": "family-1", "domain": "theoretical_biology", "cf_type": "CF1",
              "split": "final_test", "quantifier": "forall_allowed_parameters",
              "model_visible": {"problem": "public"}, "source_g5_graph_sha256": "0" * 64,
              "verification_grade": "C"}
    public_hash = hashlib.sha256(json.dumps(public, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    label = {"case_id": "case-1", "v": {"verdict": "SUPPORTED"},
             "l": {"nodes": [], "edges": []}, "u": {"node_changes": []},
             "eligible_u": True, "verifier_ref": "ref", "source_public_case_sha256": public_hash,
             "verification_grade": "C", "verification_method": "test_rulebook",
             "independent_verified": True, "synthetic_demo": False}
    plan = {"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1",
            "group_id": "G4", "diagnostic_arm": "U_ONLY", "inject_stages": ["U"],
            "paired_set_id": "family-1", "theory_family_id": "family-1", "cf_type": "CF1",
            "split": "final_test", "source_g6_arm_id": "G6_B_G4_GIVEN",
            "source_run_id": "g6-run-1", "source_checkpoint_id": "g6-cp-1",
            "profile": "theory_benchmark", "protocol_version": "g7-test-v1",
            "retry_scope": "test", "retry_protocol": "separate_frozen_retry_not_pooled",
            "replicate": 0, "arm_eligible_for_diagnostic": False}
    report = protocol_preflight([public], [label], [plan], worker_count=1, require_complete_plan=True)
    assert report["formal_run_allowed_by_protocol"] is False
    assert "g7_plan_label_eligibility_mismatch" in report["errors"]
    assert report["counts"]["g7_plan_label_eligibility_mismatches"] == ["run-1"]


def test_g7_injection_source_distinguishes_oracle_assistance_from_d0() -> None:
    label = {
        "v": {"verdict": "SUPPORTED"}, "l": {"nodes": [], "edges": []},
        "u": {"node_changes": []}, "eligible_u": False,
        "verifier_ref": "ref", "u_ineligibility_reason": "no eligible node",
    }
    d0 = injection_for({"inject_stages": []}, label)
    d1 = injection_for({"inject_stages": ["V"]}, label)
    assert d0 == {"applied_stages": [], "source": "D0_NEUTRAL_PLACEHOLDER"}
    assert d1["source"] == "ORACLE_ASSISTED_DIAGNOSIS"
    assert d1["label_source"] == "independently_verified_g7_local_labels"


def test_g7_model_message_excludes_oracle_audit_metadata() -> None:
    label = {
        "v": {"verdict": "SUPPORTED"},
        "l": {"nodes": ["claim-1"], "edges": [{"from": "claim-1", "to": "claim-2"}]},
        "u": {"node_changes": [{"claim_id": "claim-2", "to_status": "supported"}]},
        "eligible_u": True,
        "verifier_ref": "private-verifier-ref",
        "u_ineligibility_reason": "should-not-be-model-visible",
    }
    audit_payload = injection_for({"inject_stages": ["V", "L", "U"]}, label)
    visible_payload = model_visible_diagnostic_information(audit_payload)
    assert visible_payload == {
        "V": {"verdict": "SUPPORTED"},
        "L": {"nodes": ["claim-1"], "edges": [{"from": "claim-1", "to": "claim-2"}]},
        "U": {"node_changes": [{"claim_id": "claim-2", "to_status": "supported"}]},
    }
    assert "verifier_ref" not in json.dumps(visible_payload)
    assert "eligible" not in json.dumps(visible_payload)
    assert "source" not in json.dumps(visible_payload)


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


def test_g7_runner_rejects_multiworker_without_aggregate_cap_before_key_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public = tmp_path / "public.jsonl"
    labels = tmp_path / "labels.jsonl"
    plan = tmp_path / "plan.jsonl"
    public.write_text(json.dumps({"case_id": "case-1", "model_visible": {"problem": "public"}}) + "\n", encoding="utf-8")
    labels.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    plan.write_text(json.dumps({"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1"}) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "run_g7_failure_localization.py", "--public", str(public), "--labels", str(labels),
        "--plan", str(plan), "--out", str(out), "--model-id", "unused",
        "--key-file", str(tmp_path / "missing-key"), "--allow-paid", "--worker-count", "2",
    ])
    with pytest.raises(SystemExit, match="explicit aggregate cost cap"):
        g7_runner.main()
    assert not out.exists()


def test_g7_paid_evidence_gate_rejects_missing_files_without_provider_setup(tmp_path: Path) -> None:
    report = validate_paid_evidence("model-x", tmp_path / "missing-snapshot.json", tmp_path / "missing-billing.json")
    assert report["formal_paid_run_allowed_by_evidence"] is False
    assert report["evidence_status"] == "MISSING_OR_INVALID"
    assert report["errors"] == ["model_snapshot_manifest_not_found", "billing_export_not_found"]


def test_g7_paid_evidence_gate_accepts_structure_but_keeps_external_status_unverified(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    billing = tmp_path / "billing.json"
    snapshot.write_text(json.dumps({
        "model_id": "model-x",
        "gateway_weight_fingerprint": "gateway-fp-123",
        "snapshot_sha256": "a" * 64,
    }), encoding="utf-8")
    billing.write_text(json.dumps({
        "receipt_id": "receipt-1",
        "currency": "USD",
        "total_cost_usd": 1.25,
        "exported_at_utc": "2026-10-16T08:00:00+00:00",
    }), encoding="utf-8")
    report = validate_paid_evidence("model-x", snapshot, billing)
    assert report["errors"] == []
    assert report["formal_paid_run_allowed_by_evidence"] is True
    assert report["evidence_status"] == "PRESENT_UNVERIFIED_EXTERNAL"
    assert report["external_verification_claimed"] is False
    assert report["model_snapshot_manifest"]["checks"]["file_sha256"] == hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert report["billing_export"]["checks"]["file_sha256"] == hashlib.sha256(billing.read_bytes()).hexdigest()
    serialized = json.dumps(report)
    assert "receipt-1" not in serialized
    assert "1.25" not in serialized


def test_g7_paid_evidence_gate_rejects_false_snapshot_and_invalid_billing(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    billing = tmp_path / "billing.json"
    snapshot.write_text(json.dumps({
        "model_id": "other-model",
        "gateway_weight_fingerprint": False,
        "snapshot_sha256": "not-a-sha256",
    }), encoding="utf-8")
    billing.write_text(json.dumps({
        "receipt_id": "",
        "currency": "CNY",
        "total_cost_usd": float("nan"),
        "exported_at_utc": "not-a-time",
    }, allow_nan=True), encoding="utf-8")
    report = validate_paid_evidence("model-x", snapshot, billing)
    assert report["formal_paid_run_allowed_by_evidence"] is False
    assert report["errors"] == [
        "model_snapshot_model_id_mismatch",
        "model_snapshot_gateway_weight_fingerprint_missing",
        "model_snapshot_sha256_invalid",
        "billing_receipt_id_missing",
        "billing_currency_must_be_usd",
        "billing_total_cost_invalid",
        "billing_exported_at_utc_invalid",
    ]


def test_g7_runner_paid_evidence_gate_stops_before_key_or_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    public = tmp_path / "public.jsonl"
    labels = tmp_path / "labels.jsonl"
    plan = tmp_path / "plan.jsonl"
    public.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    labels.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    plan.write_text(json.dumps({"run_id": "run-1", "checkpoint_id": "cp-1", "case_id": "case-1"}) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(g7_runner, "protocol_preflight", lambda *args, **kwargs: {
        "provider_calls_made": False,
        "formal_run_allowed_by_protocol": True,
        "errors": [],
        "counts": {},
        "routing_metadata_model_prompt_hits": {},
        "forbidden_model_prompt_hits": {},
        "scientific_truth_decision_made": False,
    })
    monkeypatch.setattr(g7_runner, "OpenAICompatibleProvider", lambda **kwargs: pytest.fail("provider constructed"))
    monkeypatch.setattr(sys, "argv", [
        "run_g7_failure_localization.py", "--public", str(public), "--labels", str(labels),
        "--plan", str(plan), "--out", str(out), "--model-id", "model-x",
        "--key-file", str(tmp_path / "missing-key"), "--allow-paid",
        "--model-snapshot-manifest", str(tmp_path / "missing-snapshot.json"),
        "--billing-export", str(tmp_path / "missing-billing.json"),
    ])
    with pytest.raises(SystemExit, match="paid-evidence preflight failed"):
        g7_runner.main()
    report = json.loads((out / "g7_protocol_preflight.json").read_text(encoding="utf-8"))
    assert report["provider_calls_made"] is False
    assert report["paid_evidence"]["errors"] == ["model_snapshot_manifest_not_found", "billing_export_not_found"]


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


def test_g7_multiworker_requires_explicit_aggregate_cost_cap() -> None:
    with pytest.raises(ValueError, match="explicit aggregate cost cap"):
        effective_worker_cost_cap(16, 200.0, None)


def test_g7_aggregate_cost_cap_is_partitioned_across_workers() -> None:
    assert effective_worker_cost_cap(16, 200.0, 200.0) == pytest.approx(12.5)
    assert effective_worker_cost_cap(2, 1.0, 200.0) == pytest.approx(1.0)


def test_g7_budget_is_checked_before_a_new_model_request() -> None:
    limits = g7_runner.Limits(10, 10, 100, 1.0, total_tokens=100, cost_usd=1.0)
    with pytest.raises(RuntimeError, match="before model call"):
        limits.before_model()
    assert limits.model_calls == 0
