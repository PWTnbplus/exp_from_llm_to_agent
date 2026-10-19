import json
from pathlib import Path


ROOT = Path("runs/ctflow_single_model/20261019T-kimi-v9-prospective")


def test_v9_namespace_is_single_kimi_and_truth_separate():
    matrix = json.loads((ROOT / "PROTOCOL_NAMESPACE_MATRIX.json").read_text(encoding="utf-8"))
    assert matrix["model_id"] == "kimi-k2.5"
    assert matrix["only_base_model"] is True
    assert matrix["private_truth_not_in_public"] is True


def test_v9_readonly_audit_has_no_private_truth_value_leakage():
    audit = json.loads(Path("docs/audits/cycle-20261019T-kimi-v9/V9_INDEPENDENT_READONLY_AUDIT.json").read_text(encoding="utf-8"))
    assert audit["private_truth_value_leakage_detected"] is False
    assert audit["only_kimi_k25"] is True
    assert audit["call_numbers_contiguous"] is True
