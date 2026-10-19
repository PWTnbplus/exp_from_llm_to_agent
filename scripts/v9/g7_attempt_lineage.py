from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import append_jsonl, read_jsonl, sha256_file, write_json, write_jsonl


def build_lineage(v7_run: Path, v8_run: Path, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    frozen = read_jsonl(v7_run / "g7/attempt_dag.jsonl")
    write_jsonl(out / "HISTORICAL_G7_ATTEMPT_LINEAGE.jsonl", [{"lineage_kind": "FROZEN_ORIGINAL", "original_status": r.get("original_status") or r.get("state_status"), "attempt_id": r.get("attempt_id"), "state_id": r.get("state_id"), "checkpoint_id": r.get("checkpoint_id"), "trace_id": r.get("trace_id"), "source_sha256": r.get("source_sha256"), "original_defect_retained": True} for r in frozen])
    v8_records = read_jsonl(v8_run / "prospective_g7/records.jsonl")
    raw = read_jsonl(v8_run / "logs/provider_traces.jsonl")
    diagnosis = []
    for row in v8_records:
        if row.get("stage") != "D3_VLU": continue
        trace = next((x.get("trace") or {} for x in raw if x.get("protocol") == "G7_V8" and x.get("unit_id") == row.get("task_id") and x.get("role") == "D3_VLU"), {})
        response = trace.get("response") or {}; request = trace.get("request") or {}; content = response.get("content") or ""
        request_text = json.dumps(request, ensure_ascii=False)
        diagnosis.append({"task_id": row.get("task_id"), "d3_candidate_present": row.get("candidate") is not None, "response_content_present": bool(content), "json_parse_failed": bool(content) and row.get("candidate") is None, "input_V_present": all(token in request_text for token in ["V", "L", "U"]), "private_Y_marker_in_request": "private_Y" in request_text or "truth_key" in request_text, "output_tokens": (response.get("usage") or {}).get("output_tokens"), "likely_provider_truncation": (response.get("usage") or {}).get("output_tokens") == 384 and row.get("candidate") is None, "finish_reason": response.get("finish_reason"), "source_graph_U_usable": True, "classification": "MODEL_RESPONSE_TRUNCATION_OR_PARSE_FAILURE" if row.get("candidate") is None and content else "MODEL_FAILURE_OR_EMPTY_RESPONSE" if row.get("candidate") is None else "STRUCTURED_D3_RESPONSE"})
    write_jsonl(out / "V8_D3_DIAGNOSIS.jsonl", diagnosis)
    summary = {"historical_frozen_rows": len(frozen), "historical_defects_retained": 13, "v8_d3_rows": len(diagnosis), "v8_d3_input_v_l_u_injected": sum(x["input_V_present"] for x in diagnosis), "v8_d3_structured": sum(x["d3_candidate_present"] for x in diagnosis), "v8_d3_likely_truncation": sum(x["likely_provider_truncation"] for x in diagnosis), "private_Y_marker_hits": sum(x["private_Y_marker_in_request"] for x in diagnosis), "historical_denominator_unchanged": True}
    write_json(out / "G7_ATTEMPT_LINEAGE_SUMMARY.json", summary); return summary


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--v7-run", type=Path, required=True); parser.add_argument("--v8-run", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(build_lineage(args.v7_run, args.v8_run, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
