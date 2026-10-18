"""Run an isolated public-only Q-v2 cohort.

The cohort is deliberately separate from the frozen G7 rows.  It never reads
labels or an answer key.  A real provider is optional at the command line, but
the default safety path is a preflight-only run: paid execution requires an
explicit provider price artifact, an atomic ledger, and an explicit
``--allow-paid``.  Local SymPy verification is independent of the model's
self-reported Q value.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.v3.q_v2 import sha256_json, verify_q_record
except ModuleNotFoundError:  # direct ``python scripts/v3/run_q_v2_cohort.py``
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.v3.q_v2 import sha256_json, verify_q_record

try:
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider
except ImportError:  # pragma: no cover - direct script entry point
    OpenAICompatibleProvider = None  # type: ignore[assignment,misc]


MODEL_ID = "kimi-k2.5"
BASE_URL = "https://token.ctflow.cn/v1"
FORBIDDEN_INPUT_TERMS = (
    "g7_vlu_private", "private_oracle", "expected_decision", "correct_revised_claim",
    "hidden_true", "answer_key", "v_true", "l_true", "u_true",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(value)
    return rows


def scan_public_case(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            folded = str(key).casefold()
            if any(term in folded for term in FORBIDDEN_INPUT_TERMS):
                hits.append(f"{path}.{key}")
            hits.extend(scan_public_case(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(scan_public_case(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        folded = value.casefold()
        if any(term in folded for term in FORBIDDEN_INPUT_TERMS):
            hits.append(path)
    return hits


def public_prompt(row: dict[str, Any]) -> dict[str, Any]:
    visible = row.get("model_visible")
    if not isinstance(visible, dict):
        raise ValueError("public case lacks model_visible object")
    payload = {
        "original_problem": visible.get("original_problem"),
        "intervention_statement": visible.get("intervention_statement"),
        "original_claim": visible.get("original_claim"),
        "public_proof_graph": visible.get("public_proof_graph"),
        "instruction": (
            "Return exactly one JSON object matching the Q-v2 candidate schema. "
            "Generate one model claim only; do not mention hidden labels, routing metadata, or answer keys."
        ),
    }
    hits = scan_public_case(payload)
    if hits:
        raise ValueError(f"public prompt failed anti-leakage scan: {hits[:5]}")
    return payload


def extract_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("provider output is not a JSON object")
    return value


def q_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are in a public-only Q-v2 verification cohort. Return only JSON. "
                "The candidate must have exactly the fields claim_id, claim_type, typed_ast, "
                "assumptions, quantifiers, domain, relation, time_interval, origin. "
                "origin must be MODEL_GENERATED. For this cohort claim_type MUST be exactly "
                "monotonicity, relation MUST be one of increasing, decreasing, nonincreasing, "
                "or nondecreasing, and typed_ast MUST be a recursive object using only op/value/name/args "
                "with ops number, variable, add, sub, mul, div, pow, or neg. "
                "For example, use {\"op\":\"mul\",\"args\":[{\"op\":\"number\",\"value\":-1},{\"op\":\"variable\",\"name\":\"x\"}]} "
                "rather than a formula string. assumptions and quantifiers MUST be arrays of strings; "
                "domain MUST be an object such as {\"variable\":\"x\",\"lower\":0,\"upper\":\"infinity\"}; "
                "time_interval MUST be an object such as {\"start\":0,\"end\":\"infinity\",\"unit\":\"time\"}. "
                "Use one real variable and numeric constants in typed_ast, and state assumptions explicitly."
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def run_cohort(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.public)
    if not rows:
        raise ValueError("public cohort is empty")
    selected = rows[: args.limit] if args.limit else rows
    selected = [row for row in selected if isinstance(row.get("case_id"), str)]
    if not selected:
        raise ValueError("no public cases selected")
    prompts = []
    for row in selected:
        prompts.append({"case_id": row["case_id"], "prompt": public_prompt(row)})
    args.out.mkdir(parents=True, exist_ok=True)
    plan = {
        "protocol_id": "G7_Q_V2_PUBLIC_COHORT",
        "model_id": args.model_id,
        "base_url": args.base_url,
        "public_input": str(args.public),
        "public_sha256": sha256_file(args.public),
        "selected_cases": [p["case_id"] for p in prompts],
        "selected_case_count": len(prompts),
        "private_labels_read": False,
        "answer_key_read": False,
        "pooling_with_frozen_g7": False,
        "local_verifier": "scripts/v3/q_v2.py::verify_q_record",
        "paid_cap_usd": args.max_cost_usd,
        "pricing_evidence_provided": bool(args.pricing_evidence and args.pricing_evidence.is_file()),
        "pricing_override_used": False,
        "formal_scientific_run_allowed": False,
        "provider_calls_made": 0,
        "execution_status": "PREFLIGHT_ONLY",
    }
    (args.out / "cohort_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.preflight_only:
        return {**plan, "status": "PREFLIGHT_PASS", "reason": "explicit_preflight_only"}
    if not args.allow_paid:
        raise RuntimeError("paid Q-v2 execution requires --allow-paid; no provider request was made")
    if not args.pricing_evidence or not args.pricing_evidence.is_file():
        if not args.allow_user_authorized_unverified_pricing:
            raise RuntimeError("paid Q-v2 execution requires provider pricing evidence; no provider request was made")
        plan["pricing_override_used"] = True
        plan["execution_status"] = "USER_AUTHORIZED_UNVERIFIED_PRICING_NONCONFIRMATORY"
    (args.out / "cohort_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.cost_ledger:
        raise RuntimeError("paid Q-v2 execution requires an atomic cost ledger; no provider request was made")
    if OpenAICompatibleProvider is None:
        raise RuntimeError("provider adapter unavailable")
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("Q-v2 key file is empty")

    # Import is local so preflight-only does not initialize a paid ledger.
    from scripts.audit_repair.cost_ledger import CostLedger
    ledger = CostLedger(args.cost_ledger, global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd)
    provider = OpenAICompatibleProvider(
        api_key=key,
        base_url=args.base_url,
        model_name=args.model_id,
        timeout=args.timeout,
        max_retries=0,
        input_cost_per_1k=args.input_cost_per_1k,
        output_cost_per_1k=args.output_cost_per_1k,
        max_cost_usd=args.max_cost_usd,
        max_output_tokens=args.max_output_tokens,
        reservation_output_tokens=args.max_output_tokens,
        cost_ledger=ledger,
        ledger_scope="g7",
        ledger_worker="q-v2",
        ledger_ref_prefix="q-v2",
        require_cost_ledger=True,
    )
    records: list[dict[str, Any]] = []
    proofs = args.out / "proofs"
    proofs.mkdir(exist_ok=True)
    records_path = args.out / "q_records.jsonl"
    traces_path = args.out / "provider_traces.jsonl"
    records_path.write_text("", encoding="utf-8")
    traces_path.write_text("", encoding="utf-8")
    for item in prompts:
        provider_error = None
        response = None
        try:
            response = provider.complete(q_messages(item["prompt"]))
        except RuntimeError as exc:
            provider_error = str(exc)
        trace = provider.audit_trace()[-1] if provider.audit_trace() else {
            "call_index": len(provider.audit_trace()),
            "model": args.model_id,
            "error": {"type": "NO_PROVIDER_TRACE", "message": provider_error or "unknown"},
        }
        with traces_path.open("a", encoding="utf-8", newline="\n") as trace_handle:
            trace_handle.write(json.dumps(trace, ensure_ascii=False, separators=(",", ":")) + "\n")
        parse_error = None
        candidate = None
        if response is not None:
            try:
                candidate = extract_json_object(response.content)
            except (ValueError, json.JSONDecodeError) as exc:
                parse_error = str(exc)
        proof_path = proofs / f"{item['case_id']}.json"
        record = {
            "protocol_id": "G7_Q_V2_PUBLIC_COHORT",
            "case_id": item["case_id"],
            "model_id": args.model_id,
            "candidate": candidate,
            "q_evidence": {
                "checker_requested": True,
                "tool_call_ids": [f"q-v2-local-verifier:{item['case_id']}"],
                "verifier_input_hash": sha256_json(candidate),
                "verifier_output_ref": str(proof_path.relative_to(args.out)).replace("\\", "/"),
            },
            "provider_usage": response.usage.__dict__ if response is not None else {},
        }
        if provider_error is not None:
            record["provider_error"] = provider_error
        if parse_error is not None:
            record["parse_error"] = parse_error
        proof = verify_q_record(record)
        proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record["q_evidence"]["verifier_output_sha256"] = sha256_file(proof_path)
        records.append({**record, "independent_q": proof})
        with records_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(records[-1], ensure_ascii=False, separators=(",", ":")) + "\n")
    with records_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    result = {
        **plan,
        "status": "EXECUTED",
        "execution_status": (
            "USER_AUTHORIZED_UNVERIFIED_PRICING_NONCONFIRMATORY"
            if plan["pricing_override_used"]
            else "PAID_NONCONFIRMATORY_COHORT"
        ),
        "provider_calls_made": len(records),
        "provider_successful_responses": sum(record["provider_usage"] != {} for record in records),
        "independent_q_counts": {
            status: sum(record["independent_q"].get("status") == status for record in records)
            for status in ("PASS", "FAIL", "INCONCLUSIVE", "NOT_SCORED")
        },
    }
    (args.out / "cohort_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--key-file", type=Path, default=Path("api_key/kimi/kimi-k2.5.txt"))
    parser.add_argument("--pricing-evidence", type=Path)
    parser.add_argument("--cost-ledger", type=Path)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument(
        "--allow-user-authorized-unverified-pricing",
        action="store_true",
        help="explicit user authorization for a non-confirmatory run when provider pricing evidence is unavailable",
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--max-cost-usd", type=float, default=0.05)
    parser.add_argument("--input-cost-per-1k", type=float, default=0.001)
    parser.add_argument("--output-cost-per-1k", type=float, default=0.003)
    parser.add_argument("--max-output-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    try:
        result = run_cohort(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED_BEFORE_PROVIDER", "provider_calls_made": 0, "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
