import json
from pathlib import Path


def test_v8_d3_diagnosis_preserves_truncation_failure():
    summary = json.loads(Path("docs/audits/cycle-20261019T-kimi-v9/G7_ATTEMPT_LINEAGE_SUMMARY.json").read_text(encoding="utf-8"))
    assert summary["v8_d3_input_v_l_u_injected"] == 4
    assert summary["v8_d3_structured"] == 0
    assert summary["v8_d3_likely_truncation"] == 4


def test_v9_repair_keeps_private_y_out():
    rows = [json.loads(x) for x in Path("runs/ctflow_single_model/20261019T-kimi-v9-prospective/g7_repair/records.jsonl").read_text(encoding="utf-8").splitlines() if x]
    assert len(rows) == 16
    assert all(row["private_Y_injected"] is False for row in rows)
