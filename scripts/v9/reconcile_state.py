from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import write_json


def reconcile(state: Path, run: Path, audit: Path) -> dict:
    gates = json.loads(state.read_text(encoding="utf-8"))
    result = json.loads((audit / "V9_COMBINED_RUN_RESULT.json").read_text(encoding="utf-8"))
    entry = {"run_id": run.name, "status": "INTERNAL_RUN_COMPLETE_SCIENTIFIC_GATES_RETAINED_BLOCKED", "model_id": "kimi-k2.5", "real_provider_calls": result["api_accounting"]["real_provider_calls"], "local_usage_cost_usd": result["api_accounting"]["local_usage_cost_usd"], "protocol_counts": result["api_accounting"]["protocol_counts"], "historical_denominators_unchanged": result["historical_denominators_unchanged"], "g6_new_machine_verifiable": result["new_metrics"]["g6"], "q_new_truth_first": result["new_metrics"]["q"], "lu_u_new_control_real_sham": result["new_metrics"]["lu_u"], "g7_primary_and_repair": {"primary": result["new_metrics"]["g7_initial_public_graph_without_equation"], "repair": result["new_metrics"]["g7_repair_public_equation"]}, "scientific_release_allowed": False, "scientific_hypothesis_supported": "NO_OVERALL_SUPPORT_CLAIM", "note": "V9 internal evidence is appended. Existing historical G6/G7 gates and denominators are not rewritten; provider external attestation remains separate."}
    gates["v9_internal_execution"] = entry
    write_json(state, gates); write_json(audit / "V9_STATE_RECONCILIATION.json", {"state_path": str(state), "entry": entry, "historical_gates_preserved": True})
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--state", type=Path, required=True); parser.add_argument("--run", type=Path, required=True); parser.add_argument("--audit", type=Path, required=True); args = parser.parse_args(); print(json.dumps(reconcile(args.state, args.run, args.audit), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
