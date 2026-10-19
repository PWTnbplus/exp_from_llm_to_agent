from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/audits/cycle-20261019T094634Z-kimi-v8-real-evidence"


def _read(name: str) -> dict:
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def test_v8_internal_state_inventory_is_single_model_and_append_only() -> None:
    gates = json.loads((ROOT / "docs/state/gates.json").read_text(encoding="utf-8"))
    entry = gates["v8_internal_execution"]
    audit = _read("V8_STATE_RECONCILIATION.json")

    assert entry == {
        "run_id": audit["run_id"],
        "audit_path": "docs/audits/cycle-20261019T094634Z-kimi-v8-real-evidence/V8_STATE_RECONCILIATION.json",
        "model_id": audit["model_id"],
        "real_provider_calls": audit["real_provider_calls"],
        "protocol_counts": audit["protocol_counts"],
        "mock": audit["mock"],
        "local_usage_cost_usd": audit["local_usage_cost_usd"],
        "historical_denominators_unchanged": audit["state_preservation"]["historical_data_modified"] is False,
        "scientific_gate_uplift": False,
        "note": "Internal execution and audit inventory only. G6/G7 scientific gates remain blocked; no historical result, truth key, or denominator is changed.",
    }
    assert audit["model_id"] == "kimi-k2.5"
    assert audit["real_provider_calls"] == sum(audit["protocol_counts"].values()) == 107
    assert audit["state_preservation"]["historical_data_modified"] is False
    assert audit["state_preservation"]["truth_keys_sent_to_model"] is False
    assert audit["state_preservation"]["legacy_non_kimi_artifacts_pooled"] is False


def test_v8_reconciliation_does_not_open_scientific_gates() -> None:
    gates = json.loads((ROOT / "docs/state/gates.json").read_text(encoding="utf-8"))
    assert gates["scientific_release_allowed"] is False
    assert gates["gates"]["G6"]["status"] == "BLOCKED"
    assert gates["gates"]["G7"]["status"] == "BLOCKED"
    assert gates["v8_internal_execution"]["scientific_gate_uplift"] is False
