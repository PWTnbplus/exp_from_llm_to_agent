"""Aggregate independently audited public LU/U replicate cohorts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audits", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    audits: list[dict[str, Any]] = []
    for path in args.audits:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not value.get("engineering_audit_pass"):
            raise SystemExit(f"LU audit did not pass: {path}")
        if value.get("model_ids") != ["kimi-k2.5"]:
            raise SystemExit(f"unexpected model identity: {path}")
        audits.append(value)
    result = {
        "schema_version": 1,
        "protocol_id": "LU_V2_PUBLIC_U_REPLICATE_AGGREGATE",
        "audit_count": len(audits),
        "graphs_per_audit": sorted({int(a["graph_count"]) for a in audits}),
        "provider_calls": sum(int(a["record_count"]) for a in audits),
        "observed_transition_count": sum(int(a["observed_transition_count"]) for a in audits),
        "no_observed_state_change_count": sum(
            int((a.get("validation_error_counts") or {}).get("no observed state change", 0)) for a in audits
        ),
        "model_ids": sorted({model for audit in audits for model in audit["model_ids"]}),
        "graphs_sha256": sorted({a["graphs_sha256"] for a in audits}),
        "audit_sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in args.audits
        },
        "private_labels_read": False,
        "answer_key_read": False,
        "pooling_with_frozen_g7": False,
        "scientific_release_allowed": False,
        "interpretation": (
            "These are repeated public-only observed model transitions. The aggregate is not a causal U estimate, "
            "does not alter the frozen G7 denominator, and retains every no-change observation."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
