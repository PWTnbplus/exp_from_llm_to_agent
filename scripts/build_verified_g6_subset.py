"""Build a non-synthetic, source-only verified-family G6 analysis subset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    args = parser.parse_args()
    source = args.source
    verification = json.loads(args.verification.read_text(encoding="utf-8"))
    eligible = set(verification.get("verified_family_ids", []))
    if not eligible or verification.get("excluded_family_ids") != ["TB-L1-010"]:
        raise SystemExit("refusing subset build: independent verification report is not the expected source-only report")
    public = read_jsonl(source / "public_cases.jsonl")
    private = read_jsonl(source / "private_oracle.jsonl")
    plan = read_jsonl(source / "run_plan.jsonl")
    responses = read_jsonl(source / "responses_audited.jsonl")
    revisions = read_jsonl(source / "revision_audit.jsonl")
    family_by_case = {row["case_id"]: row["source_task_id"] for row in public}
    case_by_id = {row["case_id"]: row for row in public}
    oracle_by_case = {row["case_id"]: row for row in private}
    response_by_run = {row["run_id"]: row for row in responses}
    revision_by_run = {row["run_id"]: row for row in revisions}
    selected_public = [row for row in public if row["source_task_id"] in eligible]
    selected_private = [row for row in private if family_by_case.get(row["case_id"]) in eligible]
    selected_plan = [row for row in plan if family_by_case.get(row["case_id"]) in eligible]
    selected_responses = [response_by_run[row["run_id"]] for row in selected_plan if row["run_id"] in response_by_run]
    selected_revisions = [revision_by_run[row["run_id"]] for row in selected_plan if row["run_id"] in revision_by_run]
    if len(selected_public) != 92 or len(selected_private) != 92 or len(selected_plan) != 552 or len(selected_responses) != 552 or len(selected_revisions) != 138:
        raise SystemExit(f"unexpected subset sizes: public={len(selected_public)} private={len(selected_private)} plan={len(selected_plan)} responses={len(selected_responses)} revisions={len(selected_revisions)}")
    out = source
    write_jsonl(out / "public_cases_verified23.jsonl", selected_public)
    write_jsonl(out / "private_oracle_verified23.jsonl", selected_private)
    write_jsonl(out / "run_plan_verified23.jsonl", selected_plan)
    write_jsonl(out / "responses_verified23.jsonl", selected_responses)
    write_jsonl(out / "revision_audit_verified23.jsonl", selected_revisions)
    write_jsonl(out / "g6_to_g7_handoff_verified23.jsonl", [row for row in read_jsonl(source / "g6_to_g7_handoff.jsonl") if family_by_case.get(row["case_id"]) in eligible])
    manifest = {
        "derived_from": "formal-20261013T000000Z",
        "selection": "source-only independent verifier grade-B families; no response outcome used",
        "eligible_family_count": len(eligible),
        "excluded_family_ids": sorted(set(family_by_case.values()) - eligible),
        "public_cases": len(selected_public),
        "planned_runs": len(selected_plan),
        "responses": len(selected_responses),
        "cf3_revision_audit_rows": len(selected_revisions),
        "synthetic": False,
        "reran_provider": False,
        "raw_source_modified": False,
        "scientific_status": "CORRECTED_VERIFIED_SUBSET; ORIGINAL_576_RELEASE_RETAINED_AS_NONRELEASE",
    }
    (out / "verified23_subset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
