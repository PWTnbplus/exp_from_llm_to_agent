"""Run the Q blind-truth calibration without reading its truth key."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.v3.q_v2 import sha256_json, verify_candidate, validate_candidate
except ModuleNotFoundError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.v3.q_v2 import sha256_json, verify_candidate, validate_candidate

try:
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("provider output is not an object")
    return value


def q_messages(task: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Return only one compact JSON object with exactly claim_id, claim_type, typed_ast, assumptions, "
                "quantifiers, domain, relation, time_interval, origin. claim_type must be monotonicity and origin "
                "must be MODEL_GENERATED. Reproduce the supplied expression in typed_ast, determine relation from "
                "the supplied domain, and use increasing, decreasing, nonincreasing, or nondecreasing. Do not add fields."
            ),
        },
        {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True)},
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default="kimi-k2.5")
    parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--key-file", type=Path, default=Path("api_key/kimi/kimi-k2.5.txt"))
    parser.add_argument("--cost-ledger", type=Path, required=True)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--allow-user-authorized-unverified-pricing", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--format-retries", type=int, default=1)
    parser.add_argument("--max-cost-usd", type=float, default=8.0)
    parser.add_argument("--max-output-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    plan = json.loads((args.cohort / "cohort_plan.json").read_text(encoding="utf-8"))
    tasks = read_jsonl(args.cohort / "public_tasks.jsonl")
    if sha256(args.cohort / "public_tasks.jsonl") != plan["task_sha256"] or len(tasks) != plan["task_count"]:
        raise ValueError("public task plan hash/count mismatch")
    args.out.mkdir(parents=True, exist_ok=True)
    run_plan = {
        "protocol_id": plan["protocol_id"],
        "model_id": args.model_id,
        "base_url": args.base_url,
        "task_count": len(tasks),
        "task_sha256": plan["task_sha256"],
        "truth_key_sha256": plan["truth_key_sha256"],
        "truth_key_read_by_runner": False,
        "truth_key_sent_to_model": False,
        "private_labels_read": False,
        "pooled_with_frozen_q_v2": False,
        "format_retries": args.format_retries,
        "execution_status": "PREFLIGHT_ONLY" if args.preflight_only else "READY",
    }
    (args.out / "run_plan.json").write_text(json.dumps(run_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.preflight_only:
        print(json.dumps({**run_plan, "status": "PREFLIGHT_PASS"}, ensure_ascii=False)); return 0
    if not args.allow_paid:
        raise RuntimeError("real blind-truth cohort requires --allow-paid")
    if OpenAICompatibleProvider is None:
        raise RuntimeError("provider adapter unavailable")
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("provider key is empty")
    from scripts.audit_repair.cost_ledger import CostLedger
    ledger = CostLedger(args.cost_ledger, global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd)
    provider = OpenAICompatibleProvider(
        api_key=key, base_url=args.base_url, model_name=args.model_id, timeout=args.timeout, max_retries=0,
        input_cost_per_1k=0.001, output_cost_per_1k=0.003, max_cost_usd=args.max_cost_usd,
        max_output_tokens=args.max_output_tokens, reservation_output_tokens=args.max_output_tokens,
        cost_ledger=ledger, ledger_scope="g7", ledger_worker="q-blind-truth", ledger_ref_prefix="q-blind-truth",
        require_cost_ledger=True,
    )
    records_path = args.out / "records.jsonl"
    traces_path = args.out / "provider_traces.jsonl"
    records_path.write_text("", encoding="utf-8"); traces_path.write_text("", encoding="utf-8")
    records = []
    for task in tasks:
        response = None; candidate = None; errors: list[str] = []; start = len(provider.audit_trace()); messages = q_messages(task)
        for attempt in range(args.format_retries + 1):
            try:
                response = provider.complete(messages)
                candidate = extract_json(response.content)
                break
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(f"attempt_{attempt + 1}:{exc}")
                if attempt < args.format_retries and response is not None:
                    messages = [*messages, {"role": "assistant", "content": response.content}, {"role": "user", "content": "Return only valid compact JSON with the exact nine fields."}]
            except RuntimeError as exc:
                errors.append(str(exc)); break
        traces = provider.audit_trace()[start:]
        with traces_path.open("a", encoding="utf-8", newline="\n") as handle:
            for attempt, trace in enumerate(traces, 1):
                handle.write(json.dumps({**trace, "task_id": task["task_id"], "format_attempt": attempt}, ensure_ascii=False, separators=(",", ":")) + "\n")
        structure = None
        if candidate is not None:
            try:
                structure = validate_candidate(candidate)
            except ValueError as exc:
                structure = {"error": str(exc)}
        record = {
            "protocol_id": plan["protocol_id"], "task_id": task["task_id"], "model_id": args.model_id,
            "candidate": candidate, "structure_validation": structure, "provider_attempts": len(traces),
            "provider_usage": response.usage.__dict__ if response is not None else {}, "errors": errors,
            "private_labels_read": False, "truth_key_read": False,
        }
        records.append(record)
        with records_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    result = {**run_plan, "status": "EXECUTED", "provider_calls_made": len(provider.audit_trace()), "successful_responses": sum(bool(r["provider_usage"]) for r in records), "structured_candidates": sum(isinstance(r["structure_validation"], dict) and "error" not in r["structure_validation"] for r in records)}
    (args.out / "run_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
