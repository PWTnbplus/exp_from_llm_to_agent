"""Run paired public control/intervention state calls for LU/U calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider


def read_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"): text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    value = json.loads(text)
    if not isinstance(value, dict): raise ValueError("response is not an object")
    return value


def messages(task: dict[str, Any], arm: str, semantic_recovery: bool = False) -> list[dict[str, str]]:
    claim = task["control_claim"] if arm == "control" else task["intervention_claim"]
    payload = {
        "task_id": task["task_id"], "claim_id": task["claim_id"], "arm": arm,
        "public_domain": task["domain"], "public_claim": claim,
        "public_intervention": "No parameter change; evaluate the control claim." if arm == "control" else task["public_intervention"],
        "instruction": (
            "Return exactly one JSON object with claim_id, state_before, state_after, to_status, evidence. "
            "state_before must literally be supported for every arm. Set state_after and to_status to supported "
            "if and only if the displayed public_claim is mathematically true on x>=0; otherwise use refuted "
            "or unresolved. Evaluate the claim text exactly and ignore the task_id name. Standard weak monotonicity "
            "applies: nondecreasing means derivative >= 0, nonincreasing means derivative <= 0, so constant "
            "functions satisfy both. An intercept does not change a linear function's monotonicity."
            " For strict monotonicity, use pairwise comparison on the stated domain; an isolated endpoint "
            "derivative of zero does not by itself disprove strictness (for example, -x^2 is strictly "
            "decreasing on x>=0, while x^2 is not decreasing). Keep evidence to one short sentence "
            "(under 120 characters) so the JSON is not truncated."
        ),
        "semantic_recovery_instruction": "Recompute the derivative sign of the displayed polynomial on x>=0 and compare it directly with the stated public_claim." if semantic_recovery else None,
    }
    return [
        {"role": "system", "content": "You are in a public paired control/intervention state cohort. Return only compact JSON with exactly the five requested fields. Use no external labels or metadata. Do not reinterpret nondecreasing/nonincreasing as strict decreasing."},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default="kimi-k2.5"); parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--key-file", type=Path, default=Path("api_key/kimi/kimi-k2.5.txt")); parser.add_argument("--cost-ledger", type=Path, required=True)
    parser.add_argument("--allow-paid", action="store_true"); parser.add_argument("--allow-user-authorized-unverified-pricing", action="store_true")
    parser.add_argument("--preflight-only", action="store_true"); parser.add_argument("--format-retries", type=int, default=1)
    parser.add_argument("--semantic-recovery", action="store_true")
    parser.add_argument("--max-cost-usd", type=float, default=8.0); parser.add_argument("--max-output-tokens", type=int, default=192); parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    plan = json.loads((args.cohort / "cohort_plan.json").read_text(encoding="utf-8")); tasks = read_jsonl(args.cohort / "public_tasks.jsonl")
    if sha256(args.cohort / "public_tasks.jsonl") != plan["task_sha256"]: raise ValueError("task hash mismatch")
    args.out.mkdir(parents=True, exist_ok=True)
    run_plan = {**plan, "model_id": args.model_id, "base_url": args.base_url, "provider_call_target": len(tasks) * 2, "truth_key_read_by_runner": False, "truth_key_sent_to_model": False, "format_retries": args.format_retries, "execution_status": "PREFLIGHT_ONLY" if args.preflight_only else "READY"}
    (args.out / "run_plan.json").write_text(json.dumps(run_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.preflight_only: print(json.dumps({**run_plan, "status": "PREFLIGHT_PASS"}, ensure_ascii=False)); return 0
    if not args.allow_paid: raise RuntimeError("real LU/U causal cohort requires --allow-paid")
    if OpenAICompatibleProvider is None: raise RuntimeError("provider adapter unavailable")
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not key: raise RuntimeError("provider key is empty")
    from scripts.audit_repair.cost_ledger import CostLedger
    ledger = CostLedger(args.cost_ledger, global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd)
    provider = OpenAICompatibleProvider(api_key=key, base_url=args.base_url, model_name=args.model_id, timeout=args.timeout, max_retries=0, input_cost_per_1k=0.001, output_cost_per_1k=0.003, max_cost_usd=args.max_cost_usd, max_output_tokens=args.max_output_tokens, reservation_output_tokens=args.max_output_tokens, cost_ledger=ledger, ledger_scope="g7", ledger_worker="lu-u-causal", ledger_ref_prefix="lu-u-causal", require_cost_ledger=True)
    records_path = args.out / "records.jsonl"; traces_path = args.out / "provider_traces.jsonl"; records_path.write_text("", encoding="utf-8"); traces_path.write_text("", encoding="utf-8")
    records = []
    for task in tasks:
        for arm in ("control", "intervention"):
            response = None; candidate = None; errors: list[str] = []; start = len(provider.audit_trace()); request_messages = messages(task, arm, semantic_recovery=args.semantic_recovery)
            for attempt in range(args.format_retries + 1):
                try:
                    response = provider.complete(request_messages); candidate = extract_json(response.content); break
                except (ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"attempt_{attempt + 1}:{exc}")
                    if attempt < args.format_retries and response is not None: request_messages = [*request_messages, {"role": "assistant", "content": response.content}, {"role": "user", "content": "Return only valid compact JSON with exactly the five fields."}]
                except RuntimeError as exc: errors.append(str(exc)); break
            traces = provider.audit_trace()[start:]
            with traces_path.open("a", encoding="utf-8", newline="\n") as handle:
                for attempt, trace in enumerate(traces, 1): handle.write(json.dumps({**trace, "task_id": task["task_id"], "arm": arm, "format_attempt": attempt}, ensure_ascii=False, separators=(",", ":")) + "\n")
            validation_error = None
            if candidate is None: validation_error = "missing_candidate"
            elif set(candidate) != {"claim_id", "state_before", "state_after", "to_status", "evidence"}: validation_error = "schema_mismatch"
            elif candidate.get("claim_id") != task["claim_id"]: validation_error = "claim_id_mismatch"
            elif candidate.get("state_before") != "supported" or candidate.get("state_after") not in {"supported", "refuted", "unresolved"} or candidate.get("to_status") not in {"supported", "refuted", "unresolved"}: validation_error = "invalid_state"
            elif not isinstance(candidate.get("evidence"), str) or not candidate["evidence"].strip(): validation_error = "missing_evidence"
            record = {"protocol_id": plan["protocol_id"], "task_id": task["task_id"], "claim_id": task["claim_id"], "arm": arm, "model_id": args.model_id, "candidate": candidate, "provider_attempts": len(traces), "provider_usage": response.usage.__dict__ if response is not None else {}, "validation_error": validation_error, "errors": errors, "private_labels_read": False, "truth_key_read": False}
            records.append(record)
            with records_path.open("a", encoding="utf-8", newline="\n") as handle: handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    result = {**run_plan, "status": "EXECUTED", "provider_calls_made": len(provider.audit_trace()), "successful_responses": sum(bool(r["provider_usage"]) for r in records), "valid_records": sum(r["validation_error"] is None for r in records)}
    (args.out / "run_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
