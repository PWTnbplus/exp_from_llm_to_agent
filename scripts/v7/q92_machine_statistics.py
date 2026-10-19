from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.v7.common import read_jsonl, write_json


def stats(review: Path, out: Path) -> dict:
    rows = read_jsonl(review); counts = Counter(x.get("candidate_status") for x in rows)
    result = {"n": len(rows), "counts": dict(counts), "machine_truth_coverage": sum(x.get("machine_truth_status") != "UNKNOWN" for x in rows), "calibration_24_not_pooled": True, "historical_baseline": {"PASS": 18, "FAIL": 8, "INCONCLUSIVE": 55, "NOT_SCORED": 11}, "human_domain_review": "NOT_AVAILABLE", "scientific_release_allowed": False}
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--review", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(stats(args.review, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
