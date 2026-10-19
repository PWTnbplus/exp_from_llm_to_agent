"""Run a public-only corrective review for the 43 G6 CF3 mismatches.

This cohort is deliberately append-only and is not merged into the frozen
G6 denominator.  It supplies the model with the public boundary witness and
the previous public response, but never reads the private oracle or labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.audit_g6_cf3_public_boundary_review import SPECS
except ModuleNotFoundError:  # direct script entry point
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.audit_g6_cf3_public_boundary_review import SPECS

try:
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider


MODEL_ID = "kimi-k2.5"
BASE_URL = "https://token.ctflow.cn/v1"
DECISIONS = {"MAINTAIN", "REVISE", "REJECT", "UNDETERMINED"}
REQUIRED = {"decision", "affected_claim_ids", "revised_claim", "supporting_evidence", "boundary_handling"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}: expected JSON object")
            rows.append(value)
    return rows


def extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("provider output is not an object")
    return value


def public_payload(plan: dict[str, Any], public: dict[str, Any], prior: dict[str, Any], audit: dict[str, Any], semantic_recovery: bool = False) -> dict[str, Any]:
    visible = public.get("model_visible") or {}
    family = str(plan["case_id"]).rsplit("-CF3", 1)[0]
    spec = SPECS[family]
    return {
        "review_id": f"public-g6-cf3:{plan['run_id']}",
        "case_id": plan["case_id"],
        "public_problem": visible.get("original_problem"),
        "public_original_claim": visible.get("original_claim"),
        "public_intervention": visible.get("intervention_statement"),
        "public_boundary": {
            "parameter": spec["parameter"],
            "boundary": spec["boundary"],
            "expected_scope": spec["outcome"],
            "witness": spec["witness"],
        },
        "previous_public_response": {
            "decision": prior.get("decision"),
            "affected_claim_ids": prior.get("affected_claim_ids"),
            "revised_claim": prior.get("revised_claim"),
            "supporting_evidence": prior.get("supporting_evidence"),
        },
        "task": (
            "Independently reassess the public boundary intervention. Return one JSON object with exactly "
            "decision, affected_claim_ids, revised_claim, supporting_evidence, boundary_handling. "
            "decision must be MAINTAIN, REVISE, REJECT, or UNDETERMINED. "
            "Use the supplied public witness, do not infer any label not shown here, and do not mention "
            "routing or metadata. Explain the mathematical boundary consequence briefly in supporting_evidence."
        ),
        "previous_public_review_status": audit.get("status"),
        "semantic_recovery_instruction": (
            "This is a targeted recovery. Re-derive the displayed boundary witness before answering; "
            "distinguish the boundary case from the interior case and keep boundary_handling a non-empty string. "
            "Use the public expected_scope as the rubric: preserves_specific requires MAINTAIN; "
            "invalidates or degenerate_formula requires REVISE or REJECT. Do not replace the supplied "
            "witness with a different parameter regime or reinterpret the original numerical instance."
            if semantic_recovery else None
        ),
    }


def messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are performing a public mathematical correction review. Return only one compact JSON object. "
                "The five required fields are decision, affected_claim_ids, revised_claim, supporting_evidence, "
                "boundary_handling. Do not add fields, markdown, or a second answer."
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def retry_message() -> str:
    return (
        "Return only valid compact JSON with exactly the five required fields. "
        "No markdown and no explanation outside the JSON object."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--mismatch-audit", type=Path, required=True)
    parser.add_argument("--target-run-ids", type=Path, help="optional JSON array or newline-delimited prior run IDs")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--key-file", type=Path, default=Path("api_key/kimi/kimi-k2.5.txt"))
    parser.add_argument("--cost-ledger", type=Path, required=True)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--allow-user-authorized-unverified-pricing", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--semantic-recovery", action="store_true")
    parser.add_argument("--format-retries", type=int, default=1)
    parser.add_argument("--max-cost-usd", type=float, default=10.0)
    parser.add_argument("--max-output-tokens", type=int, default=320)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    if args.format_retries < 0 or args.format_retries > 2:
        raise SystemExit("format retries must be between 0 and 2")

    plan_rows = {row["run_id"]: row for row in read_jsonl(args.plan) if row.get("cf_type") == "CF3"}
    public_rows = {row["case_id"]: row for row in read_jsonl(args.public)}
    prior_rows = {row["run_id"]: row for row in read_jsonl(args.responses)}
    mismatch_rows = [row for row in read_jsonl(args.mismatch_audit) if row.get("status") == "FAIL"]
    if len(mismatch_rows) != 43:
        raise ValueError(f"expected exactly 43 public mismatches, found {len(mismatch_rows)}")
    target_ids: set[str] | None = None
    if args.target_run_ids:
        raw = args.target_run_ids.read_text(encoding="utf-8").strip()
        parsed = json.loads(raw) if raw.startswith("[") else [line.strip() for line in raw.splitlines() if line.strip()]
        if not isinstance(parsed, list) or not parsed or any(not isinstance(x, str) for x in parsed):
            raise ValueError("target-run-ids must contain a non-empty list of strings")
        target_ids = set(parsed)
        if len(target_ids) != len(parsed):
            raise ValueError("target-run-ids contains duplicates")
        mismatch_ids = {row.get("run_id") for row in mismatch_rows}
        if not target_ids.issubset(mismatch_ids):
            raise ValueError("target-run-ids must be a subset of the 43 public mismatches")
    selected = []
    for audit in mismatch_rows:
        run_id = audit.get("run_id")
        if run_id not in plan_rows or run_id not in prior_rows or audit.get("case_id") not in public_rows:
            raise ValueError(f"mismatch row cannot be joined: {run_id}")
        if target_ids is None or run_id in target_ids:
            selected.append((plan_rows[run_id], public_rows[audit["case_id"]], prior_rows[run_id], audit))
    if target_ids is not None and {row[0]["run_id"] for row in selected} != target_ids:
        raise ValueError("target-run-ids did not resolve to the requested rows")
    if not selected:
        raise ValueError("no rows selected for public correction review")
    args.out.mkdir(parents=True, exist_ok=True)
    plan = {
        "protocol_id": "G6_CF3_PUBLIC_MISMATCH_CORRECTION_V2" if target_ids is not None else "G6_CF3_PUBLIC_MISMATCH_CORRECTION_V1",
        "model_id": args.model_id,
        "base_url": args.base_url,
        "selected_count": len(selected),
        "selected_prior_run_ids": [row[0]["run_id"] for row in selected],
        "selected_targeted_subset": target_ids is not None,
        "plan_sha256": sha256_file(args.plan),
        "public_sha256": sha256_file(args.public),
        "prior_responses_sha256": sha256_file(args.responses),
        "mismatch_audit_sha256": sha256_file(args.mismatch_audit),
        "private_labels_read": False,
        "private_oracle_read": False,
        "pooled_with_frozen_g6": False,
        "formal_scientific_run_allowed": False,
        "format_retries": args.format_retries,
        "pricing_override_used": bool(args.allow_user_authorized_unverified_pricing and not args.preflight_only),
        "execution_status": "PREFLIGHT_ONLY" if args.preflight_only else "READY",
    }
    (args.out / "cohort_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.preflight_only:
        print(json.dumps({**plan, "status": "PREFLIGHT_PASS"}, ensure_ascii=False))
        return 0
    if not args.allow_paid:
        raise RuntimeError("real G6 correction review requires --allow-paid")
    if OpenAICompatibleProvider is None:
        raise RuntimeError("provider adapter unavailable")
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("provider key is empty")
    from scripts.audit_repair.cost_ledger import CostLedger

    ledger = CostLedger(args.cost_ledger, global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd)
    provider = OpenAICompatibleProvider(
        api_key=key,
        base_url=args.base_url,
        model_name=args.model_id,
        timeout=args.timeout,
        max_retries=0,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.003,
        max_cost_usd=args.max_cost_usd,
        max_output_tokens=args.max_output_tokens,
        reservation_output_tokens=args.max_output_tokens,
        cost_ledger=ledger,
        ledger_scope="g7",
        ledger_worker="g6-public-review",
        ledger_ref_prefix="g6-public-review",
        require_cost_ledger=True,
    )
    records_path = args.out / "review_records.jsonl"
    traces_path = args.out / "provider_traces.jsonl"
    records_path.write_text("", encoding="utf-8")
    traces_path.write_text("", encoding="utf-8")
    records: list[dict[str, Any]] = []
    for plan_row, public_row, prior, audit in selected:
        payload = public_payload(plan_row, public_row, prior, audit, semantic_recovery=args.semantic_recovery)
        response = None
        candidate = None
        errors: list[str] = []
        start = len(provider.audit_trace())
        request_messages = messages(payload)
        for attempt in range(args.format_retries + 1):
            try:
                response = provider.complete(request_messages)
                candidate = extract_json(response.content)
                break
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(f"attempt_{attempt + 1}:{exc}")
                if attempt < args.format_retries and response is not None:
                    request_messages = [
                        *request_messages,
                        {"role": "assistant", "content": response.content},
                        {"role": "user", "content": retry_message()},
                    ]
            except RuntimeError as exc:
                errors.append(str(exc))
                break
        traces = provider.audit_trace()[start:]
        with traces_path.open("a", encoding="utf-8", newline="\n") as handle:
            for attempt, trace in enumerate(traces, 1):
                handle.write(json.dumps({**trace, "review_id": payload["review_id"], "format_attempt": attempt}, ensure_ascii=False, separators=(",", ":")) + "\n")
        validation_error = None
        if candidate is not None:
            if set(candidate) != REQUIRED:
                validation_error = "response_schema_mismatch"
            elif candidate.get("decision") not in DECISIONS:
                validation_error = "invalid_decision"
            elif not isinstance(candidate.get("affected_claim_ids"), list) or any(not isinstance(x, str) for x in candidate["affected_claim_ids"]):
                validation_error = "invalid_affected_claim_ids"
            elif candidate.get("revised_claim") is not None and not isinstance(candidate.get("revised_claim"), str):
                validation_error = "invalid_revised_claim"
            elif not isinstance(candidate.get("supporting_evidence"), str) or not candidate["supporting_evidence"].strip():
                validation_error = "missing_supporting_evidence"
            elif not isinstance(candidate.get("boundary_handling"), str) or not candidate["boundary_handling"].strip():
                validation_error = "missing_boundary_handling"
        record = {
            "protocol_id": plan["protocol_id"],
            "review_id": payload["review_id"],
            "prior_run_id": plan_row["run_id"],
            "case_id": plan_row["case_id"],
            "family": plan_row.get("theory_family_id"),
            "model_id": args.model_id,
            "candidate": candidate,
            "provider_attempts": len(traces),
            "provider_usage": response.usage.__dict__ if response is not None else {},
            "validation_error": validation_error,
            "parse_or_provider_errors": errors,
            "private_labels_read": False,
            "private_oracle_read": False,
        }
        records.append(record)
        with records_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    result = {
        **plan,
        "status": "EXECUTED",
        "execution_status": "USER_AUTHORIZED_UNVERIFIED_PRICING_NONCONFIRMATORY" if plan["pricing_override_used"] else "PAID_NONCONFIRMATORY_PUBLIC_REVIEW",
        "provider_calls_made": len(provider.audit_trace()),
        "provider_successful_responses": sum(bool(row["provider_usage"]) for row in records),
        "valid_candidate_count": sum(row["candidate"] is not None and row["validation_error"] is None for row in records),
        "validation_error_counts": {},
    }
    for row in records:
        key = row["validation_error"] or "none"
        result["validation_error_counts"][key] = result["validation_error_counts"].get(key, 0) + 1
    (args.out / "cohort_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
