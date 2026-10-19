"""Independent invariant checks for a generated V5 evidence pack.

The reviewer intentionally reads only persisted derived artifacts and does not
import the pack builder or any production evaluator.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    args = parser.parse_args()
    pack = args.pack
    failures: list[str] = []
    frozen = read_jsonl(pack / "G7_FROZEN_ORIGINAL_FULL_LEDGER.jsonl")
    recovery = read_jsonl(pack / "G7_APPEND_ONLY_RECOVERY_VIEW.jsonl")
    lineage = read_jsonl(pack / "G7_RETRY_LINEAGE.jsonl")
    g6 = read_jsonl(pack / "G6_MATH_REVIEW.jsonl")
    q = read_jsonl(pack / "Q92_FROZEN_DOMAIN_REVIEW.jsonl")
    lu = read_jsonl(pack / "LU_U_PAIRED_INDEPENDENT_AUDIT.jsonl")
    if len(frozen) != 1288 or len({row.get("state_id") for row in frozen}) != 1288:
        failures.append("g7_frozen_1288_bijection")
    if sum(bool(row.get("original_defect_retained")) for row in frozen) != 13:
        failures.append("g7_historical_13_not_retained")
    if len(recovery) != 150 or len({row.get("attempt_id") for row in recovery}) != 150:
        failures.append("g7_recovery_150_unique_attempts")
    frozen_attempts = {row.get("attempt_id") for row in frozen}
    if any(row.get("parent_attempt_id") not in frozen_attempts for row in recovery):
        failures.append("g7_recovery_parent_missing")
    if len(lineage) != len(frozen) + len(recovery):
        failures.append("g7_lineage_row_count")
    if any(row.get("attempt_id") == row.get("parent_attempt_id") for row in recovery):
        failures.append("g7_retry_parent_self_reference")
    q_counts = Counter(row.get("independent_status") for row in q)
    if len(q) != 92 or dict(q_counts) != {"PASS": 18, "FAIL": 8, "INCONCLUSIVE": 55, "NOT_SCORED": 11}:
        failures.append("q92_status_counts_or_denominator")
    if any(row.get("human_domain_verdict") != "NOT_AVAILABLE" for row in q):
        failures.append("q92_human_review_overclaimed")
    if any(row.get("private_oracle_read") is not False for row in g6):
        failures.append("g6_private_oracle_boundary")
    if any(row.get("u_eligibility") == "ELIGIBLE_U" for row in lu):
        failures.append("lu_u_eligibility_without_verified_checkpoint")
    if any(row.get("validated_causal_contrast") for row in lu):
        failures.append("lu_u_unverified_contrast")
    stats = json.loads((pack / "FORMAL_STATISTICS_AUDIT.json").read_text(encoding="utf-8"))
    if stats.get("pooled_p_value_or_agent_superiority") is not None:
        failures.append("pooled_scientific_claim_present")
    if stats.get("scientific_release_allowed") is not False:
        failures.append("scientific_release_not_fail_closed")
    report = {
        "review_version": "v5-independent-read-only-review-v1",
        "review_scope": "derived evidence invariants only; no provider call; no human domain verdict",
        "input_pack": str(pack.resolve()),
        "counts": {"g7_frozen": len(frozen), "g7_recovery": len(recovery), "g7_lineage": len(lineage),
                   "g6_review": len(g6), "q92_review": len(q), "lu_u_review": len(lu)},
        "q92_status_counts": dict(q_counts),
        "g6_verdict_counts": dict(Counter(row.get("verdict") for row in g6)),
        "failures": failures,
        "engineering_review_pass": not failures,
        "scientific_release_allowed": False,
    }
    (pack / "INDEPENDENT_READ_ONLY_REVIEW.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
