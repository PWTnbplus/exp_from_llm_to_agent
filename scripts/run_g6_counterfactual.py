"""Run the G6 counterfactual protocol against a real OpenAI-compatible model.

The runner reads only public_cases.jsonl and the frozen run_plan.jsonl.  The
private oracle is intentionally not a CLI input and is never loaded here.
Each run gets an append-only event trace and one immutable response record.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scientific_discovery.models.provider import OpenAICompatibleProvider, ProviderResponse


DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}
TOOLS = [
    {"type": "function", "function": {"name": "calculate_expression", "description": "Evaluate a finite symbolic expression using only supplied numeric values.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}, "values": {"type": "object"}}, "required": ["expression"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "run_experiment", "description": "Run a bounded public-expression calculation; it cannot access hidden answers, files, or the network.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}, "values": {"type": "object"}}, "required": ["expression"], "additionalProperties": False}}},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def existing_event_seq(path: Path) -> int:
    """Return the last sequence only when an existing trace is append-safe.

    A resumed G6 invocation must never treat a malformed or non-monotonic
    trace as a valid prefix.  Returning zero in that situation would append a
    second ``seq=1`` segment and silently create a non-canonical raw trace.
    The raw file is intentionally left untouched; the caller fails closed so
    an operator can preserve it and start a separately identified retry.
    """
    if not path.is_file():
        return 0
    try:
        events = read_jsonl(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"existing G6 trace is not valid JSONL: {path}") from exc
    previous = 0
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict):
            raise RuntimeError(f"existing G6 trace row {index} is not an object: {path}")
        sequence = event.get("seq")
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise RuntimeError(f"existing G6 trace row {index} has an invalid sequence: {path}")
        expected = previous + 1
        if sequence != expected:
            raise RuntimeError(
                f"existing G6 trace sequence is not strictly contiguous at row {index}: "
                f"expected {expected}, got {sequence}: {path}"
            )
        previous = sequence
    return previous


def extract_json(text: str) -> dict[str, Any] | None:
    text = str(text or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(text[start:])
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


def parse_tool_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    raise ValueError("tool arguments must be a JSON object")


def public_math_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    expression = str(arguments.get("expression", ""))
    if len(expression) > 500:
        raise ValueError("expression too long")
    values = arguments.get("values") or {}
    if not isinstance(values, dict) or any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in values.values()):
        raise ValueError("values must contain numeric values only")
    locals_ = {str(k): sp.Float(v) for k, v in values.items()}
    expr = sp.sympify(expression, locals=locals_)
    if expr.free_symbols:
        return {"expression": str(expr), "unresolved_symbols": sorted(str(x) for x in expr.free_symbols)}
    value = float(expr.evalf())
    if not math.isfinite(value):
        raise ValueError("non-finite result")
    return {"expression": str(expr), "value": value}


def make_system(arm: str, protocol_profile: str = "legacy_project") -> str:
    if arm == "G6_A_G3_GIVEN" and protocol_profile == "g6_protocol_g3_tools_iteration":
        capability = "You are the frozen G3 Tools+Iteration arm. You may use only the listed bounded public-expression tools during the fixed two-pass workflow. The second pass is a fixed synthesis/reflection pass; do not access hidden answers or adapt the workflow beyond the bounded tool calls."
    elif arm == "G6_A_G3_GIVEN":
        capability = "You are the fixed-reflection G3 arm. You have no tools. Make one analysis pass and one fixed reflection pass."
    else:
        capability = "You are the adaptive G4 arm. You may use only the listed bounded public-expression tools and may condition later actions on their observable outputs."
    return f"""You are a counterfactual scientific-reasoning system in experiment g6_counterfactual.
{capability}
The public case includes the original problem, original claim, and a public G5 proof graph.
The intervention changes exactly one premise. Decide whether the original claim should be
MAINTAIN, REJECT, REVISE, or UNDETERMINED. Do not access files, network, hidden answers,
private oracle records, prior runs, or any answer key. Do not treat a proof-graph label as
proof by itself; reason from the public model and intervention. Return a compact JSON object
with exactly these fields: decision, affected_claim_ids, revised_claim, supporting_evidence.
decision must be one of the four labels; affected_claim_ids must be a JSON array; revised_claim
must be a string or null. Never reveal hidden reasoning or invent tool results."""


def case_prompt(case: dict[str, Any]) -> str:
    return json.dumps({"g6_case": case["model_visible"], "case_id": case["case_id"], "cf_type": case["cf_type"], "theory_family_id": case["theory_family_id"]}, ensure_ascii=False)


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    decision = str(payload.get("decision", "")).strip().upper()
    affected = payload.get("affected_claim_ids", [])
    if not isinstance(affected, list) or any(not isinstance(x, str) for x in affected):
        raise ValueError("affected_claim_ids must be a string array")
    revised = payload.get("revised_claim")
    if revised is not None and not isinstance(revised, str):
        raise ValueError("revised_claim must be string or null")
    evidence = payload.get("supporting_evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("supporting_evidence is required")
    if decision not in DECISIONS:
        raise ValueError(f"invalid decision: {decision}")
    return {"decision": decision, "affected_claim_ids": list(dict.fromkeys(affected)), "revised_claim": revised, "supporting_evidence": evidence.strip()}


@dataclass
class Limits:
    max_model_calls: int
    max_tool_calls: int
    max_total_tokens: int
    max_cost_usd: float
    model_calls: int = 0
    tool_calls: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def before_model(self) -> None:
        if self.model_calls >= self.max_model_calls:
            raise RuntimeError("global model-call hard limit exceeded")
        self.model_calls += 1

    def before_tool(self) -> None:
        if self.tool_calls >= self.max_tool_calls:
            raise RuntimeError("global tool-call hard limit exceeded")
        self.tool_calls += 1

    def consume(self, response: ProviderResponse) -> None:
        self.total_tokens += int(response.usage.input_tokens) + int(response.usage.output_tokens)
        self.cost_usd += float(response.usage.cost_usd)
        if self.total_tokens > self.max_total_tokens:
            raise RuntimeError("global token hard limit exceeded")
        if self.cost_usd > self.max_cost_usd:
            raise RuntimeError("global cost hard limit exceeded")


def existing_trace_usage(out: Path, input_cost_per_1k: float, output_cost_per_1k: float, max_output_tokens: int) -> dict[str, float | int]:
    """Recover hard-limit usage before a resumed invocation.

    G6 is append-only across interruptions.  Counting the persisted trace
    events prevents a restart from silently resetting the model/tool/token
    budget.  Provider reservation is reconstructed conservatively from each
    persisted MODEL_REQUEST, while the reported cost is summed from usage
    returned by successful MODEL_RESPONSE events.
    """
    model_calls = 0
    tool_calls = 0
    total_tokens = 0
    cost_usd = 0.0
    reserved_cost_usd = 0.0
    trace_root = out / "traces"
    if not trace_root.is_dir():
        return {"model_calls": 0, "tool_calls": 0, "total_tokens": 0, "cost_usd": 0.0, "reserved_cost_usd": 0.0}
    for event_path in trace_root.glob("*/events.jsonl"):
        try:
            events = read_jsonl(event_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        for event in events:
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "MODEL_REQUEST":
                model_calls += 1
                messages = payload.get("messages") or []
                estimated_input = max(1, len(json.dumps(messages, ensure_ascii=False).split()))
                reserved_cost_usd += (estimated_input / 1000) * input_cost_per_1k + (max_output_tokens / 1000) * output_cost_per_1k
            elif event_type == "TOOL_CALL":
                tool_calls += 1
            elif event_type == "MODEL_RESPONSE":
                usage = payload.get("usage") or {}
                input_tokens = int(usage.get("input_tokens", 0))
                output_tokens = int(usage.get("output_tokens", 0))
                total_tokens += input_tokens + output_tokens
                cost_usd += float(usage.get("cost_usd", 0.0))
    return {"model_calls": model_calls, "tool_calls": tool_calls, "total_tokens": total_tokens, "cost_usd": cost_usd, "reserved_cost_usd": reserved_cost_usd}


def emit_event(path: Path, seq: int, run_id: str, event_type: str, *, status: str, payload: dict[str, Any]) -> int:
    seq += 1
    append_jsonl(path, {"experiment_id": "g6_counterfactual", "run_id": run_id, "seq": seq, "timestamp_utc": utc_now(), "event_type": event_type, "status": status, "payload": payload})
    return seq


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in {"calculate_expression", "run_experiment"}:
        raise ValueError(f"unauthorized tool: {name}")
    result = public_math_tool(arguments)
    result["tool"] = name
    return result


def run_one(case: dict[str, Any], plan_row: dict[str, Any], provider: OpenAICompatibleProvider, limits: Limits, out: Path, request_delay: float = 0.0, protocol_profile: str = "legacy_project") -> dict[str, Any]:
    run_id = plan_row["run_id"]
    run_dir = out / "traces" / run_id
    event_path = run_dir / "events.jsonl"
    case_id = case["case_id"]
    arm = plan_row["arm_id"]
    messages: list[dict[str, Any]] = [{"role": "system", "content": make_system(arm, protocol_profile)}, {"role": "user", "content": case_prompt(case)}]
    # A Ctrl+C or transport failure can leave a partial trace.  Continue its
    # sequence rather than creating duplicate seq=1 records on resume.
    seq = existing_event_seq(event_path)
    started = time.monotonic()
    try:
        seq = emit_event(event_path, seq, run_id, "RUN_START", status="RUNNING", payload={"case_id": case_id, "arm_id": arm, "group_id": plan_row["group_id"], "model_id": provider.model_name, "protocol_profile": protocol_profile})
        protocol_g3 = protocol_profile == "g6_protocol_g3_tools_iteration" and plan_row["group_id"] == "G3"
        call_limit = 8 if protocol_g3 else (2 if plan_row["group_id"] == "G3" else 8)
        tools = TOOLS if (plan_row["group_id"] == "G4" or protocol_g3) else None
        final_payload: dict[str, Any] | None = None
        for call_index in range(call_limit):
            if plan_row["group_id"] == "G3" and call_index == 1:
                messages.append({"role": "user", "content": "Perform the fixed reflection pass now. Return only the required final JSON object."})
            limits.before_model()
            seq = emit_event(event_path, seq, run_id, "MODEL_REQUEST", status="RUNNING", payload={"call_index": call_index + 1, "messages": messages, "tools": tools})
            if request_delay:
                time.sleep(request_delay)
            response = provider.complete(messages, tools=tools)
            limits.consume(response)
            seq = emit_event(event_path, seq, run_id, "MODEL_RESPONSE", status="COMPLETED", payload={"call_index": call_index + 1, "content": response.content, "tool_calls": response.tool_calls, "usage": response.usage.__dict__, "metadata": response.metadata})
            if response.tool_calls:
                if plan_row["group_id"] != "G4" and not protocol_g3:
                    raise RuntimeError("legacy G3 returned a tool call")
                messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
                for tool_call in response.tool_calls:
                    fn = tool_call.get("function", tool_call)
                    name = str(fn.get("name", ""))
                    args = parse_tool_args(fn.get("arguments", {}))
                    limits.before_tool()
                    seq = emit_event(event_path, seq, run_id, "TOOL_CALL", status="RUNNING", payload={"tool_name": name, "tool_arguments": args})
                    try:
                        result = execute_tool(name, args)
                        tool_status = "COMPLETED"
                    except Exception as exc:
                        result = {"error_type": type(exc).__name__, "error": str(exc)}
                        tool_status = "FAILED"
                    seq = emit_event(event_path, seq, run_id, "TOOL_RESULT", status=tool_status, payload={"tool_name": name, "tool_result": result})
                    messages.append({"role": "tool", "tool_call_id": tool_call.get("id", f"tool-{limits.tool_calls}"), "name": name, "content": json.dumps(result, ensure_ascii=False)})
                continue
            parsed = extract_json(response.content)
            if parsed is not None:
                final_payload = normalize_payload(parsed)
                if protocol_g3 and call_index == 0:
                    continue
                if plan_row["group_id"] == "G3" or call_index >= 1:
                    break
        if final_payload is None:
            raise ValueError("no valid final JSON response")
        trace_ref = str(event_path.relative_to(out))
        result = {"run_id": run_id, **final_payload, "status": "completed", "trace_ref": trace_ref}
        seq = emit_event(event_path, seq, run_id, "RUN_END", status="COMPLETED", payload={"status": "completed", "elapsed_seconds": round(time.monotonic() - started, 3)})
        return result
    except Exception as exc:
        trace_ref = str(event_path.relative_to(out))
        seq = emit_event(event_path, seq, run_id, "ERROR", status="FAILED", payload={"error_type": type(exc).__name__, "error": str(exc)})
        emit_event(event_path, seq, run_id, "RUN_END", status="FAILED", payload={"status": "provider_error", "elapsed_seconds": round(time.monotonic() - started, 3)})
        return {"run_id": run_id, "decision": "UNDETERMINED", "affected_claim_ids": [], "revised_claim": None, "supporting_evidence": f"run failed: {type(exc).__name__}", "status": "provider_error", "trace_ref": trace_ref}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-cases", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--max-model-calls", type=int, required=True)
    parser.add_argument("--max-tool-calls", type=int, required=True)
    parser.add_argument("--max-total-tokens", type=int, required=True)
    parser.add_argument("--max-cost-usd", type=float, required=True)
    parser.add_argument("--input-cost-per-1k", type=float, default=0.001)
    parser.add_argument("--output-cost-per-1k", type=float, default=0.003)
    parser.add_argument("--provider-retries", type=int, default=0, help="bounded transport retries per model request; each retry is audited by the provider")
    parser.add_argument("--provider-timeout", type=int, default=60, help="bounded seconds to wait for each provider response")
    parser.add_argument("--request-delay", type=float, default=0.0, help="seconds to wait before each provider request; useful for bounded gateway pacing")
    parser.add_argument("--limit", type=int, default=0, help="bounded real smoke-run prefix; omit for the full frozen plan")
    parser.add_argument("--worker-index", type=int, default=0, help="zero-based disjoint plan shard for safe multi-key recovery")
    parser.add_argument("--worker-count", type=int, default=1, help="number of disjoint plan shards running concurrently")
    parser.add_argument("--protocol-profile", choices=("legacy_project", "g6_protocol_g3_tools_iteration"), default="legacy_project", help="legacy preserves historical semantics; the protocol profile is a new immutable-output correction")
    parser.add_argument("--expected-case-count", type=int, default=96)
    parser.add_argument("--expected-plan-rows", type=int, default=576)
    args = parser.parse_args()
    if not args.allow_paid:
        raise SystemExit("real G6 requires --allow-paid")
    if min(args.max_model_calls, args.max_tool_calls, args.max_total_tokens) <= 0 or args.max_cost_usd <= 0:
        raise SystemExit("all hard limits must be positive")
    if args.provider_retries < 0 or args.provider_retries > 2:
        raise SystemExit("provider retries must be between 0 and 2")
    if args.provider_timeout < 30 or args.provider_timeout > 300:
        raise SystemExit("provider timeout must be between 30 and 300 seconds")
    if args.request_delay < 0 or args.request_delay > 10:
        raise SystemExit("request delay must be between 0 and 10 seconds")
    if args.worker_count <= 0 or not 0 <= args.worker_index < args.worker_count:
        raise SystemExit("worker index/count must define a valid zero-based shard")
    if args.worker_count > 2:
        raise SystemExit("this controlled run permits at most 2 workers")
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise SystemExit("local key file is not a valid provider key format")
    cases = {row["case_id"]: row for row in read_jsonl(args.public_cases)}
    plan = read_jsonl(args.plan)
    if len(cases) != args.expected_case_count or len(plan) != args.expected_plan_rows:
        raise SystemExit(f"G6 input contract requires {args.expected_case_count} cases and {args.expected_plan_rows} plan rows, got {len(cases)} and {len(plan)}")
    args.out.mkdir(parents=True, exist_ok=True)
    response_path = args.out / ("responses.jsonl" if args.worker_count == 1 else f"responses.worker-{args.worker_count}-{args.worker_index}.jsonl")
    # Only a completed, schema-valid response satisfies a plan row.  Earlier
    # provider_error records remain append-only evidence and are retried on a
    # later invocation instead of being mistaken for completed science.
    response_files = [args.out / "responses.jsonl"] + sorted(args.out.glob("responses.worker-*.jsonl"))
    completed = {row.get("run_id") for path in response_files for row in read_jsonl(path) if row.get("status") == "completed"}
    prior = existing_trace_usage(args.out, args.input_cost_per_1k, args.output_cost_per_1k, 1024)
    limits = Limits(
        args.max_model_calls,
        args.max_tool_calls,
        args.max_total_tokens,
        args.max_cost_usd,
        model_calls=int(prior["model_calls"]),
        tool_calls=int(prior["tool_calls"]),
        total_tokens=int(prior["total_tokens"]),
        cost_usd=float(prior["cost_usd"]),
    )
    provider = OpenAICompatibleProvider(api_key=key, base_url=args.base_url, model_name=args.model_id, timeout=args.provider_timeout, max_retries=args.provider_retries, input_cost_per_1k=args.input_cost_per_1k, output_cost_per_1k=args.output_cost_per_1k, max_cost_usd=args.max_cost_usd, max_output_tokens=1024)
    # The provider itself enforces a worst-case reservation before every
    # request.  Restore that reservation across restarts as well as the
    # measured usage restored in Limits above.
    provider._reserved_cost_usd = float(prior["reserved_cost_usd"])
    manifest_path = args.out / ("runner_manifest.json" if args.worker_count == 1 else f"runner_manifest.worker-{args.worker_count}-{args.worker_index}.json")
    atomic_json(manifest_path, {"experiment_id": "g6_counterfactual", "model_id": args.model_id, "base_url": args.base_url, "public_cases": str(args.public_cases), "oracle_loaded": False, "allow_paid": True, "protocol_profile": args.protocol_profile, "provider_retries": args.provider_retries, "provider_timeout": args.provider_timeout, "request_delay": args.request_delay, "worker_index": args.worker_index, "worker_count": args.worker_count, "response_path": str(response_path), "hard_limits": {"max_model_calls": args.max_model_calls, "max_tool_calls": args.max_tool_calls, "max_total_tokens": args.max_total_tokens, "max_cost_usd": args.max_cost_usd}, "resume_baseline": prior, "retry_invalid_records": True, "started_at_utc": utc_now()})
    run_plan = plan if args.limit <= 0 else plan[:args.limit]
    if args.worker_count > 1:
        run_plan = [row for position, row in enumerate(run_plan) if position % args.worker_count == args.worker_index]
    for index, row in enumerate(run_plan, 1):
        if row["run_id"] in completed:
            continue
        result = run_one(cases[row["case_id"]], row, provider, limits, args.out, args.request_delay, args.protocol_profile)
        append_jsonl(response_path, result)
        if index % 10 == 0 or result["status"] != "completed":
            print(f"G6 progress {index}/{len(plan)}: {result['status']} calls={limits.model_calls} tools={limits.tool_calls} tokens={limits.total_tokens}", flush=True)
    summary_path = args.out / ("runner_summary.json" if args.worker_count == 1 else f"runner_summary.worker-{args.worker_count}-{args.worker_index}.json")
    atomic_json(summary_path, {"experiment_id": "g6_counterfactual", "model_id": args.model_id, "plan_count": len(plan), "executed_this_invocation": len(run_plan), "responses_count": len(read_jsonl(response_path)), "limits": limits.__dict__, "provider_calls": len(provider.audit_trace()), "worker_index": args.worker_index, "worker_count": args.worker_count, "completed_at_utc": utc_now()})
    print(f"G6 RUN COMPLETE: responses={len(read_jsonl(response_path))} provider_calls={len(provider.audit_trace())} worker={args.worker_index}/{args.worker_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
