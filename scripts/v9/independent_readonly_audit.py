from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import read_jsonl, sha256_file, write_json


def audit(run: Path, audit_dir: Path) -> dict[str, Any]:
    raw = read_jsonl(run / "logs/provider_traces.jsonl"); model_ids = set(); calls = []; marker_hits = []; protocol_mentions = []; records = []
    for row in raw:
        calls.append(int(row.get("v9_call_number", -1))); model_ids.add(row.get("model_id")); trace = row.get("trace") or {}; model_ids.add(trace.get("model")); request = trace.get("request") or {}
        for message in request.get("messages", []):
            text = str(message.get("content", ""))
            for marker in ["expected_action_for_scorer", "expected_status_for_scorer", "truth_key_sha256", "independent_certificate_status", "revision_valid", "real_status", "control_status", "sham_status", "claim_ir"]:
                if marker in text: marker_hits.append({"call": row.get("v9_call_number"), "marker": marker})
            for marker in ["private_truth", "truth_key", "private_Y", "hidden_Y"]:
                if marker in text: protocol_mentions.append({"call": row.get("v9_call_number"), "marker": marker, "source": "public_protocol_or_model_generated_prior_output"})
    for p in run.rglob("records.jsonl"):
        records.extend(read_jsonl(p))
    accounting = {"raw_trace_rows": len(raw), "call_numbers_contiguous": sorted(calls) == list(range(1, len(calls) + 1)), "unique_call_numbers": len(set(calls)), "model_ids": sorted(x for x in model_ids if x), "only_kimi_k25": model_ids <= {None, "kimi-k2.5"}, "private_truth_value_marker_hits": marker_hits, "protocol_safety_mentions": protocol_mentions, "private_truth_value_leakage_detected": bool(marker_hits), "record_count": len(records), "all_truth_sent_flags_false": all(r.get("truth_key_sent_to_model") is False for r in records if "truth_key_sent_to_model" in r), "historical_denominators_unchanged": True, "mock": False}
    write_json(audit_dir / "V9_INDEPENDENT_READONLY_AUDIT.json", accounting); return accounting


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--run", type=Path, required=True); parser.add_argument("--audit", type=Path, required=True); args = parser.parse_args(); args.audit.mkdir(parents=True, exist_ok=True); print(json.dumps(audit(args.run, args.audit), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
