from pathlib import Path

from scripts.v9.internal_machine_gate import build_gate


ROOT = Path(__file__).resolve().parents[1]


def test_internal_machine_gate_unlocks_only_append_only_internal_work():
    result = build_gate(
        ROOT,
        ROOT / "docs/audits/cycle-20261019T-kimi-v9/V9_COMBINED_RUN_RESULT.json",
        ROOT / "runs/ctflow_single_model/20261019T-kimi-v9-prospective",
        ROOT / "runs/ctflow_single_model/20261020T-kimi-g8-v1/g8_single_kimi_final_manifest.json",
        ROOT / "runs/ctflow_single_model/20261020T-kimi-g8-5-v1",
        ROOT / "runs/ctflow_single_model/20261020T-kimi-g7-history-pairs-v1/G7_HISTORY_PAIR_COMBINED_AUDIT.json",
        ROOT / "runs/ctflow_single_model/20261020T-kimi-g7-history-pairs-v1",
        ROOT / "tests/.tmp_internal_machine_gate.json",
    )
    assert result["internal_machine_status"] == "UNLOCKED"
    assert result["formal_scientific_release"]["status"] == "RETAINED_BLOCKED"
    assert result["formal_scientific_release"]["scientific_release_allowed"] is False
    assert result["v9"]["g7_d3"] == {
        "rows": 4,
        "semantic_correct": 3,
        "strict_correct": 0,
        "interpretation": "partial semantic diagnostic; strict status-token metric remains zero",
    }
    (ROOT / "tests/.tmp_internal_machine_gate.json").unlink()
