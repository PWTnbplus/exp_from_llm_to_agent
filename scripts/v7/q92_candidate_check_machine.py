from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json


def review(obligations: Path, truth: Path, public_review: Path, out: Path) -> dict[str, Any]:
    obs, truths, public = read_jsonl(obligations), read_jsonl(truth), read_jsonl(public_review)
    if len(obs) != len(truths) or len(obs) != len(public): raise ValueError("Q92 phase row count mismatch")
    rows = []
    for obligation, truth_row, public_row in zip(obs, truths, public):
        rows.append({
            "case_id": obligation.get("case_id"), "phase": "CANDIDATE_REVEAL",
            "machine_truth_status": truth_row.get("truth_status"),
            "candidate_status": public_row.get("independent_status"), "reason": public_row.get("reason"),
            "private_labels_read": False, "truth_key_read": False,
            "retrospective_machine_truth_first": True,
        })
    write_jsonl(out, rows)
    result = {"row_count": len(rows), "candidate_status_counts": {s: sum(x["candidate_status"] == s for x in rows) for s in ("PASS", "FAIL", "INCONCLUSIVE", "NOT_SCORED")}, "truth_key_read": False, "pooled_with_frozen_q92": False, "source_hashes": {"obligations": sha256_file(obligations), "truth": sha256_file(truth), "public_review": sha256_file(public_review)}}
    write_json(out.with_name("Q92_CANDIDATE_CHECK_MANIFEST.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--obligations", type=Path, required=True); parser.add_argument("--truth", type=Path, required=True); parser.add_argument("--public-review", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(review(args.obligations, args.truth, args.public_review, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
