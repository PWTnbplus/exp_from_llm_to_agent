#!/usr/bin/env python3
"""Freeze a full, non-pooled G7 rerun after a protocol repair."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def readl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, source_id: str) -> str:
    return f"{prefix}_{hashlib.sha256(source_id.encode('utf-8')).hexdigest()[:20]}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    source = readl(args.source_plan)
    if not source:
        raise SystemExit("source plan is required")
    source_runs = {row["run_id"] for row in source}
    source_checkpoints = {row["checkpoint_id"] for row in source}
    if len(source_runs) != len(source) or len(source_checkpoints) > len(source):
        raise SystemExit("source plan has invalid run/checkpoint identifiers")
    rows: list[dict[str, Any]] = []
    for row in source:
        retry = dict(row)
        retry["run_id"] = stable_id("g7full", row["run_id"])
        retry["checkpoint_id"] = stable_id("g7fullcp", row["checkpoint_id"])
        retry["source_run_id"] = row["run_id"]
        retry["source_checkpoint_id"] = row["checkpoint_id"]
        retry["retry_scope"] = "all_original_rows_protocol_corrected"
        retry["retry_protocol"] = "separate_frozen_retry_not_pooled"
        retry["protocol_version"] = "g7-public-case-format-retry-v1"
        rows.append(retry)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    manifest = {
        "kind": "g7_full_protocol_corrected_retry_plan",
        "status": "FROZEN_SEPARATE_RETRY",
        "source_plan": str(args.source_plan),
        "source_plan_sha256": sha256(args.source_plan),
        "retry_plan_sha256": sha256(args.out),
        "source_plan_rows": len(source),
        "retry_rows": len(rows),
        "retry_unique_source_runs": len({row["source_run_id"] for row in rows}),
        "retry_unique_source_checkpoints": len({row["source_checkpoint_id"] for row in rows}),
        "pooling_prohibited": True,
        "format_retry_protocol": {
            "version": "g7-public-case-format-retry-v1",
            "max_format_retries_per_workflow": 1,
            "new_scientific_observation_added": False,
            "repair_message_is_fixed": True,
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
