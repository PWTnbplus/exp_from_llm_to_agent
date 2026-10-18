"""Independent, pre-specified statistical audit for a public Q-v2 cohort.

The input contains model-generated candidates and an independent local verifier,
not a truth key.  This script therefore reports the planned estimands and their
intervals, while explicitly refusing to label the result as scientific
confirmation.  It never reads hidden labels or legacy G7 decisions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

try:
    from scipy.stats import beta as beta_distribution
except ImportError:  # pragma: no cover - the research environment includes SciPy
    beta_distribution = None

try:
    from scripts.v3.q_v2 import verify_q_record
except ModuleNotFoundError:  # direct script entry point
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.v3.q_v2 import verify_q_record


STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "NOT_SCORED")


def read_records(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(row)
    return rows


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = (p + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt((p * (1.0 - p) / total) + z * z / (4.0 * total * total)) / denominator
    return [max(0.0, centre - half), min(1.0, centre + half)]


def metric(name: str, successes: int, total: int) -> dict[str, Any]:
    exact_interval = None
    if beta_distribution is not None and total > 0:
        alpha = 0.05
        exact_interval = [
            0.0 if successes == 0 else float(beta_distribution.ppf(alpha / 2.0, successes, total - successes + 1)),
            1.0 if successes == total else float(beta_distribution.ppf(1.0 - alpha / 2.0, successes + 1, total - successes)),
        ]
    return {
        "name": name,
        "successes": successes,
        "total": total,
        "proportion": (successes / total) if total else None,
        "wilson_95_ci": wilson(successes, total),
        "clopper_pearson_exact_95_ci": exact_interval,
        "method": "Wilson score interval, z=1.959963984540054; exact Clopper-Pearson interval when available",
    }


def plan() -> dict[str, Any]:
    return {
        "primary_estimand": "PASS / all selected public cases",
        "secondary_estimand": "PASS / (PASS + FAIL), excluding unsupported or invalid cases",
        "missingness": "INCONCLUSIVE and NOT_SCORED remain in the primary denominator and are not imputed",
        "interval": "two-sided 95% Wilson score interval plus Clopper-Pearson exact interval when SciPy is available",
        "unit": "one public case, one final independent verifier verdict",
        "truth_requirement": "an external blinded truth set is required for confirmatory scientific accuracy",
        "multiple_testing": "no claim-specific hypothesis testing; this is a prespecified audit of two descriptive estimands",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = read_records(args.records)
    if not rows:
        raise SystemExit("no Q-v2 records")
    case_ids = [row.get("case_id") for row in rows]
    if any(not isinstance(case_id, str) or not case_id for case_id in case_ids):
        raise SystemExit("every record must have a non-empty case_id")
    if len(set(case_ids)) != len(case_ids):
        raise SystemExit("duplicate case_id; refusing statistical aggregation")

    verdicts = [verify_q_record(row) for row in rows]
    counts = {status: sum(v.get("status") == status for v in verdicts) for status in STATUSES}
    scoreable = counts["PASS"] + counts["FAIL"]
    retry_count = sum(row.get("format_retry_used") is True for row in rows)
    parsed_count = sum(isinstance(row.get("candidate"), dict) for row in rows)
    parse_error_count = sum(bool(row.get("parse_errors")) for row in rows)
    actual_call_count = sum(int(row.get("provider_attempts", 0) or 0) for row in rows)

    analysis_plan = plan()
    plan_hash = hashlib.sha256(
        json.dumps(analysis_plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    result = {
        "schema_version": 1,
        "protocol_id": "G7_Q_V2_PUBLIC_COHORT_CONFIRMATORY_STATISTICAL_AUDIT",
        "records_sha256": hashlib.sha256(args.records.read_bytes()).hexdigest(),
        "record_count": len(rows),
        "case_id_count": len(set(case_ids)),
        "recomputed_status_counts": counts,
        "provider_attempt_count_from_records": actual_call_count,
        "format_retry_case_count": retry_count,
        "parsed_candidate_case_count": parsed_count,
        "cases_with_parse_errors": parse_error_count,
        "analysis_plan": analysis_plan,
        "analysis_plan_sha256": plan_hash,
        "metrics": [
            metric("primary_pass_fraction_all_selected", counts["PASS"], len(rows)),
            metric("secondary_pass_fraction_scoreable", counts["PASS"], scoreable),
        ],
        "confirmatory_scientific_status": "BLOCKED",
        "confirmatory_scientific_reason": (
            "The cohort has no independent blinded truth labels; local Q-v2 proofs establish only "
            "the whitelisted symbolic property of a submitted candidate. Unsupported and invalid "
            "cases are retained as missing/non-scoreable and no truth accuracy claim is made."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
