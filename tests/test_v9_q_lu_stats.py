import json
from pathlib import Path


def test_v9_q_and_lu_terminal_counts():
    q = json.loads(Path("docs/audits/cycle-20261019T-kimi-v9/Q_V9_REVIEW_SUMMARY.json").read_text(encoding="utf-8"))
    lu = json.loads(Path("docs/audits/cycle-20261019T-kimi-v9/LU_U_V9_SUMMARY.json").read_text(encoding="utf-8"))
    assert q["rows"] == 8 and q["state_correct"] == 8
    assert lu["arm_counts"] == {"CONTROL": 4, "REAL": 4, "SHAM": 4}
