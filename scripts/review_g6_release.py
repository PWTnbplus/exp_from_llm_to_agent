"""Independent read-only release review for the derived G6 artifact set.

This intentionally does not import the G6 runner or the post-run audit helper.
It checks the frozen denominator, hashes, required deliverables, score shape,
and the scientific-release blocker independently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-model-id", default="glm-5")
    parser.add_argument("--expected-base-url", default="https://token.ctflow.cn/v1")
    args = parser.parse_args()
    root = args.out

    # The repaired G6 protocol is an append-only, two-worker run and does not
    # reuse the historical 576-row release bundle.  Review it from its own
    # manifests and post-run audits; retain the legacy branch below for the
    # previously published artifact layout.
    corrected_audit_path = root / "g6_audit" / "audit.json"
    corrected_manifests = sorted(root.glob("runner_manifest*.json"))
    if corrected_manifests and corrected_audit_path.is_file():
        failures: list[str] = []
        plan = read_jsonl(root / "run_plan.jsonl")
        responses = read_jsonl(root / "responses_audited.jsonl")
        public = read_jsonl(root / "public_cases.jsonl")
        private = read_jsonl(root / "private_oracle.jsonl")
        handoff = read_jsonl(root / "g6_to_g7_handoff.jsonl")
        audit = read_json(corrected_audit_path)
        trace_repair = read_json(root / "trace_repair_manifest.json")
        merge_manifest = read_json(root / "responses_merge_manifest.json")
        manifests = [read_json(path) for path in corrected_manifests]

        expected = {
            "plan": 552,
            "public": 92,
            "private": 92,
            "handoff": 552,
        }
        counts = {
            "plan": len(plan),
            "responses": len(responses),
            "public": len(public),
            "private": len(private),
            "handoff": len(handoff),
        }
        for name, value in expected.items():
            if counts[name] != value:
                failures.append(f"{name}_count:{counts[name]}:{value}")
        if len({row.get("run_id") for row in plan}) != expected["plan"]:
            failures.append("plan_run_id_uniqueness")
        if len({row.get("run_id") for row in responses}) != expected["plan"]:
            failures.append("response_run_id_uniqueness")
        if {row.get("run_id") for row in plan} != {row.get("run_id") for row in responses}:
            failures.append("response_plan_bijection")
        if len({row.get("case_id") for row in public}) != expected["public"]:
            failures.append("public_case_id_uniqueness")
        if len({row.get("case_id") for row in private}) != expected["private"]:
            failures.append("private_case_id_uniqueness")
        if any(row.get("status") != "completed" for row in responses):
            failures.append("non_completed_canonical_response")
        if audit.get("pass") is not True or audit.get("plan_count") != expected["plan"] or audit.get("trace_count") != expected["plan"]:
            failures.append("g6_audit")
        if trace_repair.get("audited_response_count") != expected["plan"] or trace_repair.get("failed_to_extract_successful_attempt"):
            failures.append("trace_repair")
        if merge_manifest.get("selected_completed_rows") != expected["plan"] or merge_manifest.get("missing_run_ids"):
            failures.append("response_merge")
        profiles = {manifest.get("protocol_profile") for manifest in manifests}
        workers = {manifest.get("worker_count") for manifest in manifests}
        if profiles != {"g6_protocol_g3_tools_iteration"}:
            failures.append(f"protocol_profile:{sorted(profiles)}")
        if workers != {2}:
            failures.append(f"worker_count:{sorted(workers)}")
        for manifest in manifests:
            if manifest.get("model_id") != args.expected_model_id or manifest.get("base_url") != args.expected_base_url:
                failures.append("manifest_model_or_base_url")
            if manifest.get("oracle_loaded") is not False or manifest.get("allow_paid") is not True:
                failures.append("manifest_isolation_or_paid_flag")

        actual_hashes = {
            rel: digest(root / rel)
            for rel in ("run_plan.jsonl", "public_cases.jsonl", "private_oracle.jsonl", "responses_audited.jsonl", "g6_to_g7_handoff.jsonl")
        }
        result = {
            "review": "independent_g6_release_review",
            "artifact_root": str(root.resolve()),
            "protocol_layout": "corrected_g6_protocol_g3_tools_iteration",
            "structural_review_pass": not failures,
            "scientific_release_allowed": False,
            "failures": failures,
            "counts": counts,
            "hashes": actual_hashes,
            "protocol_profile": sorted(profiles),
            "worker_counts": sorted(workers),
            "g6_audit_pass": audit.get("pass"),
            "revision_valid_count": audit.get("revision_valid_count"),
            "note": "Structural completeness does not override the G5 independent-math, upstream provenance, or verified-model-snapshot blockers.",
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if not failures else 2

    failures: list[str] = []
    required = [
        "manifest.json", "G6_MANIFEST.json", "G6_SOURCE_INDEX.json",
        "public_cases.jsonl", "private_oracle.jsonl", "run_plan.jsonl",
        "responses_audited.jsonl", "trace_audit.json", "score_report_audited.json",
        "g6_to_g7_handoff.jsonl", "audit_g5_inputs.md", "preregistration.md",
        "reports/G6_REPORT.md",
    ]
    for rel in required:
        if not (root / rel).is_file():
            failures.append(f"missing:{rel}")

    plan = read_jsonl(root / "run_plan.jsonl")
    responses = read_jsonl(root / "responses_audited.jsonl")
    public = read_jsonl(root / "public_cases.jsonl")
    private = read_jsonl(root / "private_oracle.jsonl")
    handoff = read_jsonl(root / "g6_to_g7_handoff.jsonl")
    plan_ids = [row.get("run_id") for row in plan]
    response_ids = [row.get("run_id") for row in responses]
    if len(plan) != 576 or len(set(plan_ids)) != 576:
        failures.append(f"plan_denominator:{len(plan)}:{len(set(plan_ids))}")
    if len(responses) != 576 or len(set(response_ids)) != 576 or set(plan_ids) != set(response_ids):
        failures.append("response_plan_bijection")
    if len(public) != 96 or len({row.get("case_id") for row in public}) != 96:
        failures.append("public_cases")
    if len(private) != 96 or len({row.get("case_id") for row in private}) != 96:
        failures.append("private_oracle")
    if len(handoff) != 576:
        failures.append(f"handoff_count:{len(handoff)}")
    if any(row.get("status") != "completed" for row in responses):
        failures.append("non_completed_canonical_response")

    manifest = read_json(root / "manifest.json")
    if manifest.get("scientific_release_allowed") is not False:
        failures.append("release_flag_not_blocked")
    if manifest.get("status") != "EXECUTION_COVERAGE_COMPLETE_BUT_SCIENTIFIC_ACCEPTANCE_BLOCKED":
        failures.append("manifest_status")
    trace = read_json(root / "trace_audit.json")
    if trace.get("pass") is not True or trace.get("trace_count") != 576:
        failures.append("trace_audit")
    score = read_json(root / "score_report_audited.json")
    if score.get("run_count") != 576 or score.get("provided_response_count") != 576:
        failures.append("score_denominator")
    for arm in ("G6_A_G3_GIVEN", "G6_B_G4_GIVEN"):
        block = (score.get("by_arm") or {}).get(arm) or {}
        if block.get("planned") != 288 or block.get("valid_outputs") != 288 or block.get("completion_rate") != 1.0:
            failures.append(f"arm:{arm}")

    expected_hashes = {
        "run_plan.jsonl": "757bbe375ca2af474a0dcf3a009a889265d6ce2ba62ff488d37427cedb426c30",
        "public_cases.jsonl": "14724d44df832dfb836bf6e493fb880886c2695cdc593accd7fea9943dfcf953",
        "private_oracle.jsonl": "32c8f47c9897d9630e146af315672fc3f9ecee81d498ab893b734c23a3d1cafd",
        "responses_audited.jsonl": "bddb0981ae795b6e1faf9b8b8151852afa03dcc820299963ca4c1126a3c81c0b",
    }
    actual_hashes = {rel: digest(root / rel) for rel in expected_hashes}
    for rel, expected in expected_hashes.items():
        if actual_hashes[rel] != expected:
            failures.append(f"hash:{rel}")

    source_index = read_json(root / "G6_SOURCE_INDEX.json")
    source_mismatches = []
    for row in source_index.get("source_rows", []):
        path = Path(row["graph_path"])
        if not path.is_file() or digest(path) != row.get("graph_sha256"):
            source_mismatches.append(row.get("task_id"))
    if len(source_index.get("source_rows", [])) != 24 or source_mismatches:
        failures.append(f"g5_source_integrity:{source_mismatches}")

    result = {
        "review": "independent_g6_release_review",
        "artifact_root": str(root.resolve()),
        "structural_review_pass": not failures,
        "scientific_release_allowed": False,
        "failures": failures,
        "counts": {
            "plan": len(plan), "responses": len(responses), "public": len(public),
            "private": len(private), "handoff": len(handoff),
        },
        "hashes": actual_hashes,
        "g5_source_rows": len(source_index.get("source_rows", [])),
        "note": "Structural completeness does not override the G5 independent-math and verified-model-snapshot blockers.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
