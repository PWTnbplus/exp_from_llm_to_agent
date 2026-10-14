"""Build a G6-to-G7 handoff from the final audited G6 response view.

The handoff is metadata only.  It does not alter model responses or infer a
scientific answer; oracle fields are copied from the independently verified
G6 input and response fields are copied from the selected completed records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    plan = {str(row["run_id"]): row for row in read_jsonl(args.plan)}
    oracle = {str(row["case_id"]): row for row in read_jsonl(args.oracle)}
    responses = {str(row["run_id"]): row for row in read_jsonl(args.responses)}
    missing = sorted(set(plan) - set(responses))
    if missing:
        raise SystemExit(f"cannot build handoff: missing completed responses for {len(missing)} run_ids")

    rows: list[dict[str, Any]] = []
    for run_id, p in plan.items():
        response = responses[run_id]
        o = oracle[p["case_id"]]
        decision = response.get("decision")
        rows.append({
            "affected_claim_ids": response.get("affected_claim_ids", []),
            "arm_id": p["arm_id"],
            "case_id": p["case_id"],
            "cf_type": p["cf_type"],
            "decision": decision,
            "expected_decision": o["expected_decision"],
            "failure_type": "decision_correct" if decision == o["expected_decision"] else "decision_incorrect",
            "is_mock": False,
            "oracle_affected_claim_ids": o.get("affected_claim_ids", []),
            "run_id": run_id,
            "theory_family_id": p["theory_family_id"],
            "trace_ref": response["trace_ref"],
        })
    write_jsonl(args.out, rows)
    print(json.dumps({"rows": len(rows), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
