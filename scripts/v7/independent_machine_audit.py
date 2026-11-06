from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, sha256_file, write_json


REQUIRED = {
    "BASELINE_MANIFEST.json", "EXECUTION_EVENTS.jsonl", "G6_276_MACHINE_ADJUDICATION.jsonl", "G6_FROZEN_552_SEPARATION.json",
    "G7_1288_FROZEN_AND_150_RECOVERY.json", "G7_13_HISTORICAL_DEFECT_LINEAGE.jsonl", "G7_AUTOMATED_REANALYSIS.json",
    "Q92_TRUTH_FIRST_MACHINE_REVIEW.jsonl", "Q92_MACHINE_COUNTS_AND_24_CALIBRATION.json", "LU_CERTIFIED_EDGES_AND_U_TRANSITIONS.jsonl",
    "LU_PROSPECTIVE_CAUSAL_MACHINE_STATS.json", "SINGLE_KIMI_PROVIDER_LOCAL_LEDGER.json", "AUTOMATED_TEST_RESULTS.json", "SOURCE_AND_RESULT_SHA256.json",
}


def audit(audit_dir: Path, run_dir: Path, out: Path) -> dict:
    failures: list[str] = []
    names = {x.name for x in audit_dir.iterdir() if x.is_file()}
    failures.extend("missing:" + name for name in sorted(REQUIRED - names))
    manifest = json.loads((audit_dir / "BASELINE_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("model_id") != "kimi-k2.5" or manifest.get("language_model_count") != 1: failures.append("single_model_manifest")
    g6 = read_jsonl(audit_dir / "G6_276_MACHINE_ADJUDICATION.jsonl")
    if len(g6) != 276: failures.append("g6_row_count")
    if json.loads((audit_dir / "G6_FROZEN_552_SEPARATION.json").read_text(encoding="utf-8")).get("denominator_changed"): failures.append("g6_denominator_changed")
    g7 = read_jsonl(audit_dir / "G7_13_HISTORICAL_DEFECT_LINEAGE.jsonl")
    if len(g7) != 13: failures.append("g7_defect_count")
    q = read_jsonl(audit_dir / "Q92_TRUTH_FIRST_MACHINE_REVIEW.jsonl")
    forbidden = ("truth_key", "private_labels", "answer_key", "hidden_true")
    for row in q:
        if any(key in row and row.get(key) not in (False, None, "UNKNOWN") for key in forbidden): failures.append("q_truth_leak")
    traces = []
    trace_path = run_dir / "lu" / "pairs.jsonl"
    for pair in read_jsonl(trace_path) if trace_path.exists() else []:
        for record_key in ("control_record", "real_intervention_record"):
            record = pair.get(record_key) or {}
            observed = record.get("model_id")
            if observed:
                observed_models = set(observed if isinstance(observed, list) else [observed])
                if observed_models != {"kimi-k2.5"}: failures.append("non_kimi_model")
    events = read_jsonl(audit_dir / "EXECUTION_EVENTS.jsonl")
    if not events: failures.append("empty_execution_events")
    result = {"independent_reviewer": "v7-independent-machine-audit-v1", "failures": sorted(set(failures)), "required_files_checked": len(REQUIRED), "g6_rows": len(g6), "g7_defect_rows": len(g7), "q92_rows": len(q), "event_rows": len(events), "audit_sha256": sha256_file(audit_dir / "SOURCE_AND_RESULT_SHA256.json"), "scientific_release_allowed": False}
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--audit-dir", type=Path, required=True); parser.add_argument("--run-dir", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); result = audit(args.audit_dir, args.run_dir, args.out); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not result["failures"] else 2


if __name__ == "__main__": raise SystemExit(main())
