import json
from pathlib import Path


def test_v9_final_result_is_not_a_scientific_superiority_claim():
    result = json.loads(Path("docs/audits/cycle-20261019T-kimi-v9/V9_COMBINED_RUN_RESULT.json").read_text(encoding="utf-8"))
    assert result["api_accounting"]["real_provider_calls"] == 104
    assert result["completion_states"]["SCIENTIFIC_HYPOTHESIS_SUPPORTED"] == "NO_OVERALL_SUPPORT_CLAIM"
    assert result["historical_denominators_unchanged"]["g6_machine_rows"] == 276
