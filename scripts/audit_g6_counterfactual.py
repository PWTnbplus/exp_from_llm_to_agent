"""Independent post-run integrity and CF3 revision audit for formal G6."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}
ALLOWED_TOOLS = {"calculate_expression", "run_experiment"}
PRIVATE_VALUE_FIELDS = ("correct_revised_claim", "counterexample", "oracle_reason")
REVISION_REF = "g6_private_oracle_grade_c_postrun_revision_rubric_v1"
SUPPORTED_PROTOCOL_PROFILES = {"legacy_project", "g6_protocol_g3_tools_iteration"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def index_unique(rows: list[dict[str, Any]], field: str, label: str) -> tuple[dict[Any, dict[str, Any]], list[str]]:
    """Index rows without allowing duplicate records to be silently replaced."""

    indexed: dict[Any, dict[str, Any]] = {}
    failures: list[str] = []
    for row in rows:
        value = row[field]
        if value in indexed:
            failures.append(f"duplicate_{label}:{value}")
            continue
        indexed[value] = row
    return indexed, failures


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def parsed_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        result = {str(key) for key in value}
        for child in value.values():
            result.update(nested_keys(child))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for child in value:
            result.update(nested_keys(child))
        return result
    return set()


def segments(events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    result: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for event in events:
        if event.get("event_type") == "RUN_START" and current:
            result.append(current)
            current = []
        current.append(event)
    if current:
        result.append(current)
    return result


def load_manifests(out: Path) -> tuple[list[dict[str, Any]], list[str]]:
    manifests: list[dict[str, Any]] = []
    failures: list[str] = []
    for path in sorted(out.glob("runner_manifest*.json")):
        try:
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"manifest:{path.name}:{type(exc).__name__}")
    return manifests, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--trace-audit", type=Path, required=True)
    parser.add_argument("--revision-audit", type=Path, required=True)
    parser.add_argument("--expected-plan-count", type=int, default=576)
    parser.add_argument("--expected-public-count", type=int, default=96)
    parser.add_argument("--expected-private-count", type=int, default=96)
    parser.add_argument("--expected-cf3-count", type=int, default=144)
    parser.add_argument("--expected-model-id", default="glm-5")
    parser.add_argument("--expected-base-url", default="https://token.ctflow.cn/v1")
    args = parser.parse_args()

    plan = read_jsonl(args.plan)
    public = read_jsonl(args.public)
    private = read_jsonl(args.private)
    responses = read_jsonl(args.responses)
    failures: list[str] = []
    plan_by_run, plan_index_failures = index_unique(plan, "run_id", "plan_run_id")
    private_by_case, private_index_failures = index_unique(private, "case_id", "private_case_id")
    response_by_run, response_index_failures = index_unique(responses, "run_id", "response_run_id")
    failures.extend(plan_index_failures)
    failures.extend(private_index_failures)
    failures.extend(response_index_failures)
    missing_private_cases = sorted({row["case_id"] for row in plan} - set(private_by_case))
    if missing_private_cases:
        failures.append(f"missing_private_cases:{missing_private_cases}")
    checks = Counter()
    manifests, manifest_failures = load_manifests(args.out)
    failures.extend(manifest_failures)
    profiles = {str(manifest.get("protocol_profile")) for manifest in manifests}
    if profiles - SUPPORTED_PROTOCOL_PROFILES or len(profiles) != 1:
        failures.append(f"protocol_profile:{sorted(profiles)}")
    protocol_profile = next(iter(profiles), "legacy_project")

    if len(plan) != args.expected_plan_count or len(plan_by_run) != args.expected_plan_count:
        failures.append(f"plan_count:{len(plan)}:{len(plan_by_run)}")
    if len(public) != args.expected_public_count or len({row["case_id"] for row in public}) != args.expected_public_count:
        failures.append("public_case_count_or_uniqueness")
    if len(private) != args.expected_private_count or len(private_by_case) != args.expected_private_count:
        failures.append("private_oracle_count_or_uniqueness")
    if len(responses) != len(response_by_run) or set(response_by_run) != set(plan_by_run):
        failures.append("response_plan_bijection")

    expected_private_fields = {"expected_decision", "affected_claim_ids", *PRIVATE_VALUE_FIELDS}
    for oracle in private:
        if oracle.get("verification_grade") != "C" or oracle.get("verifier_status") != "verified":
            failures.append(f"oracle_grade_or_status:{oracle.get('case_id')}")
        if not expected_private_fields.issubset(oracle):
            failures.append(f"oracle_fields:{oracle.get('case_id')}")

    all_private_text = [norm_text(oracle.get(field)) for oracle in private for field in PRIVATE_VALUE_FIELDS if oracle.get(field)]
    trace_count = 0
    model_request_count = 0
    model_response_count = 0
    tool_call_count = 0
    tool_result_count = 0
    total_tokens = 0
    total_cost = 0.0
    segment_statuses: Counter[str] = Counter()
    for run_id, response in response_by_run.items():
        plan_row = plan_by_run.get(run_id)
        if plan_row is None:
            continue
        required = {"run_id", "decision", "affected_claim_ids", "revised_claim", "supporting_evidence", "status", "trace_ref"}
        if set(response) != required:
            failures.append(f"response_fields:{run_id}")
        if response.get("status") != "completed" or response.get("decision") not in DECISIONS:
            failures.append(f"response_status_or_decision:{run_id}")
        if not isinstance(response.get("affected_claim_ids"), list) or any(not isinstance(x, str) for x in response["affected_claim_ids"]):
            failures.append(f"response_claim_ids:{run_id}")
        if response.get("revised_claim") is not None and not isinstance(response.get("revised_claim"), str):
            failures.append(f"response_revision_type:{run_id}")
        if not isinstance(response.get("supporting_evidence"), str) or not response["supporting_evidence"].strip():
            failures.append(f"response_evidence:{run_id}")
        trace_ref = response.get("trace_ref")
        if not isinstance(trace_ref, str):
            failures.append(f"trace_ref_type:{run_id}")
            continue
        trace_path = (args.out / trace_ref).resolve()
        try:
            trace_path.relative_to(args.out.resolve())
        except ValueError:
            failures.append(f"trace_escape:{run_id}")
            continue
        if not trace_path.is_file():
            failures.append(f"trace_missing:{run_id}")
            continue
        trace_count += 1
        try:
            events = read_jsonl(trace_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"trace_invalid:{run_id}:{type(exc).__name__}")
            continue
        seqs = [event.get("seq") for event in events]
        if seqs != list(range(1, len(events) + 1)):
            failures.append(f"trace_seq:{run_id}")
        if any(event.get("experiment_id") != "g6_counterfactual" or event.get("run_id") != run_id for event in events):
            failures.append(f"trace_identity:{run_id}")
        run_segments = segments(events)
        if not run_segments or (run_segments[-1][-1].get("event_type") != "RUN_END" or (run_segments[-1][-1].get("payload") or {}).get("status") != "completed"):
            failures.append(f"trace_final_status:{run_id}")
        for segment in run_segments:
            if segment and segment[-1].get("event_type") == "RUN_END":
                segment_statuses[str((segment[-1].get("payload") or {}).get("status"))] += 1
        for event in events:
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "MODEL_REQUEST":
                model_request_count += 1
                messages = payload.get("messages") or []
                request_text = norm_text(messages)
                if any(secret and secret in request_text for secret in all_private_text):
                    failures.append(f"private_value_in_request:{run_id}")
                key_set = set()
                for message in messages:
                    # Only model-visible system/user inputs can leak the
                    # private oracle. Assistant/tool messages are prior model
                    # outputs or authorized public observations.
                    if isinstance(message, dict) and message.get("role") in {"system", "user"}:
                        key_set.update(nested_keys(parsed_json(message.get("content"))))
                if key_set & expected_private_fields:
                    failures.append(f"private_field_in_request:{run_id}")
            elif event_type == "MODEL_RESPONSE":
                model_response_count += 1
                metadata = payload.get("metadata") or {}
                if metadata.get("model") != args.expected_model_id:
                    failures.append(f"model_id:{run_id}")
                usage = payload.get("usage") or {}
                if not {"input_tokens", "output_tokens", "cost_usd"}.issubset(usage):
                    failures.append(f"usage_fields:{run_id}")
                total_tokens += int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
                total_cost += float(usage.get("cost_usd", 0.0))
            elif event_type == "TOOL_CALL":
                tool_call_count += 1
                name = (payload.get("tool_name") or "")
                if plan_row["group_id"] == "G3" and protocol_profile == "legacy_project":
                    failures.append(f"g3_tool_call:{run_id}")
                if name not in ALLOWED_TOOLS:
                    failures.append(f"unauthorized_tool:{run_id}:{name}")
            elif event_type == "TOOL_RESULT":
                tool_result_count += 1

    for manifest in manifests:
        if manifest.get("model_id") != args.expected_model_id or manifest.get("base_url") != args.expected_base_url:
            failures.append("manifest_model_or_base_url")
        if manifest.get("oracle_loaded") is not False:
            failures.append("manifest_oracle_loaded")
        if int(manifest.get("worker_count", 0)) != 2:
            failures.append(f"worker_count_not_two:{manifest.get('worker_count')}")

    revision_rows: list[dict[str, Any]] = []
    for plan_row in plan:
        if plan_row["cf_type"] != "CF3":
            continue
        oracle = private_by_case.get(plan_row["case_id"])
        response = response_by_run.get(plan_row["run_id"])
        if oracle is None or response is None:
            continue
        decision_ok = response.get("decision") == oracle.get("expected_decision")
        claims_ok = set(response.get("affected_claim_ids", [])) == set(oracle.get("affected_claim_ids", []))
        revision_ok = bool(response.get("revised_claim")) and norm_text(response.get("revised_claim")) == norm_text(oracle.get("correct_revised_claim"))
        revision_rows.append({"run_id": plan_row["run_id"], "is_valid": bool(decision_ok and claims_ok and revision_ok), "independent_verifier_ref": REVISION_REF})

    args.revision_audit.parent.mkdir(parents=True, exist_ok=True)
    args.revision_audit.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in revision_rows), encoding="utf-8")
    audit = {
        "experiment_id": "g6_counterfactual",
        "plan_count": len(plan),
        "response_count": len(responses),
        "trace_count": trace_count,
        "model_request_count": model_request_count,
        "model_response_count": model_response_count,
        "tool_call_count": tool_call_count,
        "tool_result_count": tool_result_count,
        "total_tokens_from_responses": total_tokens,
        "total_cost_usd_from_responses": round(total_cost, 9),
        "segment_end_statuses": dict(segment_statuses),
        "revision_audit_count": len(revision_rows),
        "revision_valid_count": sum(row["is_valid"] for row in revision_rows),
        "plan_sha256": sha256(args.plan),
        "public_sha256": sha256(args.public),
        "private_oracle_sha256": sha256(args.private),
        "canonical_responses_sha256": sha256(args.responses),
        "manifest_count": len(manifests),
        "protocol_profile": protocol_profile,
        "worker_counts": sorted({manifest.get("worker_count") for manifest in manifests}),
        "failures": failures,
        "pass": not failures and trace_count == len(plan) and len(revision_rows) == args.expected_cf3_count,
        "scientific_caveat": "The private oracle is grade C controlled-intervention evidence; this audit does not upgrade it to independent domain-grade A/B truth.",
    }
    args.trace_audit.parent.mkdir(parents=True, exist_ok=True)
    args.trace_audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))
    return 0 if audit["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
