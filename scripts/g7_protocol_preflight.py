#!/usr/bin/env python3
"""Preflight the model-facing G7 protocol without making provider calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_g7_failure_localization import protocol_preflight


def readl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker-count", type=int, default=16)
    args = parser.parse_args()

    public_rows = readl(args.public)
    label_rows = readl(args.labels)
    plan_rows = readl(args.plan)
    report = protocol_preflight(public_rows, label_rows, plan_rows, args.worker_count,
                                require_complete_plan=True)
    report.update({
        "input_hashes": {
            "public": sha256(args.public),
            "labels": sha256(args.labels),
            "plan": sha256(args.plan),
        },
        "runner_contract": "scripts/run_g7_failure_localization.py::case_prompt",
    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
