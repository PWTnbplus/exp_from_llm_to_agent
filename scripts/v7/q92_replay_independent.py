from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, sha256_file, write_json


def replay(review: Path, truth: Path, out: Path) -> dict:
    rows, truths = read_jsonl(review), read_jsonl(truth)
    failures = []
    if len(rows) != len(truths): failures.append("row_count_mismatch")
    if any(x.get("private_labels_read") for x in rows): failures.append("private_label_leak")
    result = {"rows_replayed": len(rows), "truth_rows": len(truths), "failures": failures, "review_sha256": sha256_file(review), "truth_sha256": sha256_file(truth), "independent_read_only": True}
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--review", type=Path, required=True); parser.add_argument("--truth", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); result = replay(args.review, args.truth, args.out); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not result["failures"] else 2


if __name__ == "__main__": raise SystemExit(main())
