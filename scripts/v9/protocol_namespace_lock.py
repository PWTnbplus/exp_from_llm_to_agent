from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import sha256_file, write_json


def lock(root: Path, cohort_id: str, model_id: str = "kimi-k2.5") -> dict:
    if model_id != "kimi-k2.5":
        raise ValueError("namespace lock rejects non-Kimi model")
    rows = []
    for name in ("g6", "q", "lu", "g7", "agent_comparison"):
        base = root / name
        public = base / "public_cases.jsonl"
        private = base / "private_truth.jsonl"
        plan = base / "plan.json"
        if not public.exists() or not plan.exists():
            raise FileNotFoundError(f"missing frozen public or plan: {base}")
        if name != "agent_comparison" and not private.exists():
            raise FileNotFoundError(f"missing frozen private truth: {base}")
        rows.append({"namespace": name, "cohort_id": cohort_id, "public_sha256": sha256_file(public), "plan_sha256": sha256_file(plan), "private_truth_sha256": sha256_file(private) if private.exists() else None, "model_id": model_id})
    matrix = {"schema_version": 1, "cohort_id": cohort_id, "model_id": model_id, "base_url": "https://token.ctflow.cn/v1", "only_base_model": True, "namespaces": rows, "private_truth_not_in_public": True, "frozen_before_provider_calls": True}
    write_json(root / "PROTOCOL_NAMESPACE_MATRIX.json", matrix)
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True); parser.add_argument("--cohort-id", required=True)
    args = parser.parse_args(); print(json.dumps(lock(args.root, args.cohort_id), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
