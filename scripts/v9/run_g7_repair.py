from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build_g7_repair import build
from .g7_checkpoint_fork_runner import run_g7
from .provider import SingleKimiProvider
from .common import sha256_file, write_json


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--run", type=Path, required=True); parser.add_argument("--key-file", type=Path, required=True); parser.add_argument("--base-url", default="https://token.ctflow.cn/v1"); parser.add_argument("--max-cost", type=float, default=20.0); parser.add_argument("--timeout", type=float, default=90.0); args = parser.parse_args()
    base = args.run / "g7_repair"
    if not (base / "public_cases.jsonl").exists(): build(base)
    provider = SingleKimiProvider(args.run, args.key_file, args.base_url, "kimi-k2.5", args.max_cost, args.timeout)
    result = run_g7(provider, base)
    write_json(args.run / "G7_REPAIR_NAMESPACE_MATRIX.json", {"cohort_id": "20261019T-kimi-v9-g7-repair", "model_id": "kimi-k2.5", "public_sha256": sha256_file(base / "public_cases.jsonl"), "plan_sha256": sha256_file(base / "plan.json"), "private_truth_sha256": sha256_file(base / "private_truth.jsonl"), "private_Y_injected": False, "separate_from_primary_g7": True})
    (args.run / "G7_REPAIR_EXECUTION.json").write_text(json.dumps({"model_id": "kimi-k2.5", "cohort_id": "G7_KIMI_V9_REPAIR_PUBLIC_EQUATION", "result": result, "call_count": provider.call_no, "private_Y_injected": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
