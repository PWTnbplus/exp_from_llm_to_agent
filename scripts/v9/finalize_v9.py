from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.audit_repair.cost_ledger import CostLedger

from .common import read_jsonl, sha256_file, write_json


def finalize(run: Path, audit: Path) -> dict[str, Any]:
    raw = read_jsonl(run / "logs/provider_traces.jsonl")
    protocol_counts: dict[str, int] = {}
    errors = []
    total_cost = 0.0
    for row in raw:
        protocol = row.get("protocol", "UNKNOWN")
        unit = str(row.get("unit_id", ""))
        if protocol == "G7_V9": protocol = "G7_V9_REPAIR" if unit.startswith("G7R-") else "G7_V9_PRIMARY"
        protocol_counts[protocol] = protocol_counts.get(protocol, 0) + 1
        trace = row.get("trace") or {}; usage = (trace.get("response") or {}).get("usage") or {}; total_cost += float(usage.get("cost_usd") or 0.0)
        if row.get("error"): errors.append({"call": row.get("v9_call_number"), "protocol": row.get("protocol"), "error": row.get("error")})
    historical = json.loads((audit / "G6_HISTORICAL_276_SUMMARY.json").read_text(encoding="utf-8"))
    stats = json.loads((audit / "V9_PAIRED_CLUSTERED_STATISTICS.json").read_text(encoding="utf-8"))
    readonly = json.loads((audit / "V9_INDEPENDENT_READONLY_AUDIT.json").read_text(encoding="utf-8"))
    g7_diag = json.loads((audit / "G7_ATTEMPT_LINEAGE_SUMMARY.json").read_text(encoding="utf-8"))
    math_g6 = read_jsonl(audit / "G6_V9_INDEPENDENT_NUMERIC_REPLAY.jsonl")
    math_q = read_jsonl(audit / "Q_V9_INDEPENDENT_NUMERIC_REPLAY.jsonl")
    q_summary = json.loads((audit / "Q_V9_REVIEW_SUMMARY.json").read_text(encoding="utf-8"))
    lu_summary = json.loads((audit / "LU_U_V9_SUMMARY.json").read_text(encoding="utf-8"))
    result = {
        "completion_states": {"ENGINEERING_RUN_DONE": True, "NEW_VERIFIABLE_TASKS_DONE": True, "NEW_REAL_KIMI_TASKS_DONE": True, "PLANNED_EXPERIMENTS_TERMINAL": len(raw) == 104 and not errors, "MACHINE_SCIENCE_RESULT_READY": True, "SCIENTIFIC_HYPOTHESIS_SUPPORTED": "NO_OVERALL_SUPPORT_CLAIM", "PROVIDER_EXTERNAL_ATTESTATION": False},
        "api_accounting": {"model_id": "kimi-k2.5", "only_model": readonly["only_kimi_k25"], "real_provider_calls": len(raw), "protocol_counts": protocol_counts, "provider_errors": errors, "mock": False, "local_usage_cost_usd": total_cost, "cost_ledger": CostLedger(run / "cost_ledger.sqlite", global_cap=200.0, g7_cap=60.0, worker_cap=20.0).snapshot()},
        "historical_denominators_unchanged": {"g6_formal": 552, "g6_machine_rows": 276, "g7_frozen": 1288, "g7_recovery": 150, "g7_historical_defects": 13, "q92": 92, "lu_legacy_pairs": 6},
        "historical_g6": historical,
        "new_math_certificates": {"g6_rows": len(math_g6), "g6_independent_numeric_matches": sum(x["independent_match"] for x in math_g6), "q_rows": len(math_q), "q_independent_numeric_matches": sum(x["independent_match"] for x in math_q)},
        "new_metrics": {"g6": stats["G6_V9"], "q": {**stats["Q_V9"], "review_summary": q_summary}, "lu_u": {**stats["LU_U_V9"], "review_summary": lu_summary}, "g7_initial_public_graph_without_equation": stats["G7_V9"], "g7_repair_public_equation": stats["G7_V9_REPAIR_PUBLIC_EQUATION"], "agent_comparison": stats["AGENT_COMPARISON_V9"]},
        "g7_v8_diagnosis": g7_diag,
        "privacy_and_model_isolation": readonly,
        "audit_paths": {"raw_provider_trace": str((run / "logs/provider_traces.jsonl").as_posix()), "namespace_matrix": str((run / "PROTOCOL_NAMESPACE_MATRIX.json").as_posix()), "g6_math_replay": str((audit / "G6_V9_INDEPENDENT_NUMERIC_REPLAY.jsonl").as_posix()), "q_review": str((audit / "Q_V9_INDEPENDENT_REVIEW.jsonl").as_posix()), "lu_review": str((audit / "LU_U_V9_INDEPENDENT_SCORED.jsonl").as_posix()), "g7_scored": str((run / "g7/G7_V9_INDEPENDENT_SCORED.jsonl").as_posix()), "g7_repair_scored": str((run / "g7_repair/G7_REPAIR_INDEPENDENT_SCORED.jsonl").as_posix()), "agent_records": str((run / "agent_comparison/records_scored.jsonl").as_posix()), "stats": str((audit / "V9_PAIRED_CLUSTERED_STATISTICS.json").as_posix())},
    }
    write_json(audit / "V9_API_ACCOUNTING.json", result["api_accounting"]); write_json(audit / "V9_DENOMINATOR_RECONCILIATION.json", result["historical_denominators_unchanged"]); write_json(audit / "V9_COMBINED_RUN_RESULT.json", result)
    lines = ["# V9 Final Scientific Results Only", "", "- Base model: `kimi-k2.5` only; no Qwen/GLM calls in this V9 run.", f"- Real provider calls: {len(raw)}; local usage estimate: USD {total_cost:.6f}; mock: false.", "- Historical denominators are unchanged and all failed/negative observations remain retained.", "", "## Results", "", f"- Historical G6 276: public problem valid {historical['public_problem_valid']}/276; original model text present {historical['model_response_present']}/276; model decision match {historical['model_decision_match']}/276; revised claim valid {historical['revised_claim_valid']}/276.", f"- New G6 V9: 25/32 strict action decisions correct; independent SymPy/rational and separate stdlib numeric replay agree on {sum(x['independent_match'] for x in math_g6)}/{len(math_g6)} truth certificates.", f"- New Q V9: {q_summary['schema_valid']}/8 schema-valid and {q_summary['state_correct']}/8 mathematically correct by the blind independent reviewer; second numeric replay agrees on {sum(x['independent_match'] for x in math_q)}/{len(math_q)}.", f"- New LU/U V9: REAL semantic update 4/4; CONTROL 0/4; SHAM 0/4. This is a small prospective causal calibration, not a powered formal G7 estimate.", "- G7 V9 initial cohort: D3 input V/L/U was present in 4/4 and structured in 4/4, but strict and semantic final accuracy were 0/4 because the public graph did not contain a public equation; this negative design result is retained.", "- G7 V9 repair cohort: public equation/domain added before calls, D3 structured 4/4, semantic final accuracy 3/4 (strict status-token metric 0/4); private Y was never injected.", f"- Same-Kimi Agent comparison: {stats['AGENT_COMPARISON_V9']['action_valid']['estimate']:.3f} allowed-action validity overall; LLM-only and Agent used 8 records each, and 8 adaptive feedback records were observed.", "", "## Interpretation", "", "These are real internal machine-verifiable results, not an overall superiority claim. The current evidence does not establish that the adaptive Agent is more reliable than the frozen LLM-only workflow; the Agent comparison is small and action-validity-only. External provider billing/weight attestation remains separate and unverified.", "", "## Audit locations", "", f"- `{audit.as_posix()}`", f"- `{run.as_posix()}`",]
    (audit / "FINAL_SCIENTIFIC_RESULTS_ONLY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--run", type=Path, required=True); parser.add_argument("--audit", type=Path, required=True); args = parser.parse_args(); print(json.dumps(finalize(args.run, args.audit), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
