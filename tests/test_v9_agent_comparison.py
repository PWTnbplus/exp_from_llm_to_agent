import json
from pathlib import Path


def test_v9_agent_comparison_is_same_model_and_adaptive():
    stats = json.loads(Path("docs/audits/cycle-20261019T-kimi-v9/V9_PAIRED_CLUSTERED_STATISTICS.json").read_text(encoding="utf-8"))
    comparison = stats["AGENT_COMPARISON_V9"]
    assert comparison["adaptive_feedback_records"] == 8
    assert comparison["by_workflow"]["LLM_ONLY"]["n"] == 8
    assert comparison["by_workflow"]["AGENT"]["n"] == 8
