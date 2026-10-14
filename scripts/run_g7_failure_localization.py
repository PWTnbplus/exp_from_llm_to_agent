#!/usr/bin/env python3
"""Real-provider G7 checkpoint/fork runner.

The runner is intentionally separate from ``g7_offline.py``.  It reads public
cases and the independently reviewed G7 local labels only to apply the
diagnostic intervention; it never sends the G6 private oracle or prior G6
model answers to the provider.  Checkpoints are actual new provider calls and
are never backfilled from G6.

The response contract below is deliberately explicit because malformed stage
objects are recorded as invalid provider attempts, not silently repaired.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.scientific_discovery.models.provider import OpenAICompatibleProvider, ProviderResponse
from run_g6_counterfactual import TOOLS, execute_tool, parse_tool_args, extract_json


DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def readl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}: expected JSON object")
            rows.append(value)
    return rows


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(path: Path, seq: int, run_id: str, event_type: str, status: str, payload: dict[str, Any]) -> int:
    seq += 1
    append_jsonl(path, {"seq": seq, "ts_utc": utc_now(), "run_id": run_id,
                        "event_type": event_type, "status": status, "payload": payload})
    return seq


def parse_payload(content: str) -> dict[str, Any]:
    value = extract_json(content)
    if not isinstance(value, dict):
        raise ValueError("provider response did not contain a JSON object")
    decision = str(value.get("decision", value.get("final_decision", ""))).upper().strip()
    if decision not in DECISIONS:
        raise ValueError(f"invalid decision {decision!r}")
    value["decision"] = decision
    return value


def normalize_stages(value: dict[str, Any]) -> dict[str, Any]:
    stages = value.get("stages")
    if not isinstance(stages, dict):
        raise ValueError("missing stages object")
    for stage in ("V", "L", "U", "Q"):
        if stage not in stages or not isinstance(stages[stage], dict):
            raise ValueError(f"missing stage {stage}")
    if stages["V"].get("verdict") not in {"SUPPORTED", "CONTRADICTED", "INDETERMINATE"}:
        raise ValueError("invalid V verdict")
    if not isinstance(stages["L"].get("nodes"), list) or not isinstance(stages["L"].get("edges"), list):
        raise ValueError("invalid L stage")
    if not isinstance(stages["U"].get("node_changes"), list):
        raise ValueError("invalid U stage")
    if not isinstance(stages["Q"].get("verdict", ""), str):
        raise ValueError("invalid Q stage")
    return stages


def system_prompt(group: str) -> str:
    if group == "G3":
        protocol = ("You are the frozen G3 Tools+Iteration checkpoint/fork arm. Use only the bounded public-expression tools, "
                    "and use a fixed second synthesis pass. Do not change the workflow based on hidden information.")
    else:
        protocol = ("You are the adaptive G4 checkpoint/fork arm. You may use only the bounded public-expression tools "
                    "and may condition later public tool calls on their observable outputs.")
    return f"""You are a real-provider participant in experiment g7_failure_localization, profile theory_benchmark.
{protocol}
The case is public and contains a scientific problem, claim, intervention, and public proof graph.
Never access files, network, hidden answers, G6 private oracle records, prior G6 responses, or answer keys.
For a checkpoint, reason from the public case only and return JSON with decision, affected_claim_ids,
revised_claim, supporting_evidence. For a diagnostic fork, the user message may contain staged V/L/U
diagnostic information. Apply only the stages explicitly supplied, then return JSON with exactly:
decision, affected_claim_ids, revised_claim, supporting_evidence, stages. stages must contain:
V={{"verdict":"SUPPORTED|CONTRADICTED|INDETERMINATE"}},
L={{"nodes":[claim_id strings],"edges":[{{"from":claim_id,"to":claim_id}}]}},
U={{"node_changes":[{{"claim_id":claim_id,"to_status":"supported|rejected|uncertain"}}]}},
and Q={{"verdict":string,"reason":string}}. Use empty arrays when there are no edges or
node changes. Do not use decision labels such as REJECT in V.verdict, do not use arrow strings
for L edges, and do not use an object/map for U.node_changes. decision values are MAINTAIN,
REJECT, REVISE, or UNDETERMINED. Do not reveal hidden chain-of-thought."""


def case_prompt(case: dict[str, Any]) -> str:
    return json.dumps({"g7_public_case": case["model_visible"], "case_id": case["case_id"],
                       "cf_type": case["cf_type"], "theory_family_id": case["theory_family_id"]},
                      ensure_ascii=False)


def public_tool_loop(provider: OpenAICompatibleProvider, messages: list[dict[str, Any]],
                     group: str, limits: "Limits", event_path: Path, trace_id: str,
                     seq: int, checkpoint: bool) -> tuple[dict[str, Any], int]:
    max_calls = 2 if group == "G3" else 8
    tools = TOOLS
    parsed = None
    for call_index in range(max_calls):
        if group == "G3" and call_index == 1:
            messages.append({"role": "user", "content": "Perform the fixed second synthesis pass. Return only the required JSON."})
        limits.before_model()
        seq = emit(event_path, seq, trace_id, "MODEL_REQUEST", "RUNNING",
                   {"call_index": call_index + 1, "checkpoint": checkpoint, "messages": messages, "tools": tools})
        response = provider.complete(messages, tools=tools)
        limits.consume(response)
        seq = emit(event_path, seq, trace_id, "MODEL_RESPONSE", "COMPLETED",
                   {"call_index": call_index + 1, "checkpoint": checkpoint, "content": response.content,
                    "tool_calls": response.tool_calls, "usage": response.usage.__dict__,
                    "metadata": response.metadata})
        if response.tool_calls:
            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
            for tool_call in response.tool_calls:
                fn = tool_call.get("function", tool_call)
                name = str(fn.get("name", ""))
                args = parse_tool_args(fn.get("arguments", {}))
                limits.before_tool()
                seq = emit(event_path, seq, trace_id, "TOOL_CALL", "RUNNING",
                           {"tool_name": name, "tool_arguments": args})
                try:
                    result = execute_tool(name, args)
                    tool_status = "COMPLETED"
                except Exception as exc:
                    result = {"error_type": type(exc).__name__, "error": str(exc)}
                    tool_status = "FAILED"
                seq = emit(event_path, seq, trace_id, "TOOL_RESULT", tool_status,
                           {"tool_name": name, "tool_result": result})
                messages.append({"role": "tool", "tool_call_id": tool_call.get("id", f"tool-{limits.tool_calls}"),
                                 "name": name, "content": json.dumps(result, ensure_ascii=False)})
            continue
        parsed = parse_payload(response.content)
        if checkpoint and group == "G3" and call_index == 0:
            continue
        if checkpoint or call_index >= 1:
            break
    if parsed is None:
        raise ValueError("no valid JSON response")
    return parsed, seq


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
        if self.total_tokens > self.max_total_tokens or self.cost_usd > self.max_cost_usd:
            raise RuntimeError("G7 hard budget exceeded")


def persisted_usage(out: Path, input_rate: float, output_rate: float, max_output_tokens: int) -> dict[str, float | int]:
    usage = {"model_calls": 0, "tool_calls": 0, "total_tokens": 0, "cost_usd": 0.0, "reserved_cost_usd": 0.0}
    for path in out.glob("**/*.jsonl"):
        for event in readl(path):
            typ = event.get("event_type")
            if typ == "MODEL_REQUEST":
                usage["model_calls"] += 1
                messages = event.get("payload", {}).get("messages", [])
                usage["reserved_cost_usd"] += (max(1, len(json.dumps(messages, ensure_ascii=False).split())) / 1000) * input_rate
                usage["reserved_cost_usd"] += (max_output_tokens / 1000) * output_rate
            elif typ == "TOOL_CALL":
                usage["tool_calls"] += 1
            elif typ == "MODEL_RESPONSE":
                u = event.get("payload", {}).get("usage", {})
                usage["total_tokens"] += int(u.get("input_tokens", 0)) + int(u.get("output_tokens", 0))
                usage["cost_usd"] += float(u.get("cost_usd", 0.0))
    return usage


def injection_for(row: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    stages = row["inject_stages"]
    injection: dict[str, Any] = {"applied_stages": [], "source": "independently_verified_g7_local_labels"}
    if "V" in stages:
        injection["V"] = {"verdict": label["v"]["verdict"], "verifier_ref": label["verifier_ref"]}
        injection["applied_stages"].append("V")
    if "L" in stages:
        injection["L"] = {"nodes": label["l"]["nodes"], "edges": label["l"]["edges"], "verifier_ref": label["verifier_ref"]}
        injection["applied_stages"].append("L")
    if "U" in stages:
        injection["U"] = {"node_changes": label["u"]["node_changes"], "eligible": label["eligible_u"],
                           "reason": label.get("u_ineligibility_reason"), "verifier_ref": label["verifier_ref"]}
        injection["applied_stages"].append("U")
    return injection


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model-id", required=True)
    p.add_argument("--key-file", type=Path, required=True)
    p.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    p.add_argument("--allow-paid", action="store_true")
    p.add_argument("--worker-index", type=int, default=0)
    p.add_argument("--worker-count", type=int, default=1)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--provider-retries", type=int, default=0)
    p.add_argument("--provider-timeout", type=float, default=60)
    p.add_argument("--input-cost-per-1k", type=float, default=0.001)
    p.add_argument("--output-cost-per-1k", type=float, default=0.003)
    p.add_argument("--max-model-calls", type=int, default=4608)
    p.add_argument("--max-tool-calls", type=int, default=3456)
    p.add_argument("--max-total-tokens", type=int, default=4608000)
    p.add_argument("--max-cost-usd", type=float, default=200.0)
    args = p.parse_args()
    if not args.allow_paid:
        raise SystemExit("real G7 requires explicit --allow-paid")
    if args.worker_count < 1 or args.worker_count > 16 or not 0 <= args.worker_index < args.worker_count:
        raise SystemExit("worker_count must be between 1 and 16 and worker_index must be in range")
    public = {x["case_id"]: x for x in readl(args.public)}
    labels = {x["case_id"]: x for x in readl(args.labels)}
    plan = readl(args.plan)
    if not public or not plan:
        raise SystemExit("public cases and plan are required")
    for row in plan:
        if row["case_id"] not in public or row["case_id"] not in labels:
            raise SystemExit(f"plan row lacks public case or G7 label: {row.get('run_id')}")
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / f"states.worker-{args.worker_count}-{args.worker_index}.jsonl"
    checkpoint_path = out / f"checkpoints.worker-{args.worker_count}-{args.worker_index}.jsonl"
    prior_states = {x["run_id"]: x for x in readl(state_path)}
    prior_cp = {x["checkpoint_id"]: x for x in readl(checkpoint_path) if x.get("status") == "completed"}
    usage = persisted_usage(out, args.input_cost_per_1k, args.output_cost_per_1k, 1024)
    limits = Limits(args.max_model_calls, args.max_tool_calls, args.max_total_tokens, args.max_cost_usd,
                    int(usage["model_calls"]), int(usage["tool_calls"]), int(usage["total_tokens"]), float(usage["cost_usd"]))
    provider = OpenAICompatibleProvider(api_key=args.key_file.read_text(encoding="utf-8").strip(), base_url=args.base_url,
                                        model_name=args.model_id, timeout=args.provider_timeout, max_retries=args.provider_retries,
                                        input_cost_per_1k=args.input_cost_per_1k, output_cost_per_1k=args.output_cost_per_1k,
                                        max_cost_usd=args.max_cost_usd, max_output_tokens=1024)
    selected = plan if args.limit <= 0 else plan[:args.limit]
    checkpoints: dict[str, dict[str, Any]] = {}
    for row in selected:
        checkpoints.setdefault(row["checkpoint_id"], row)
    selected_cps = {cp: row for cp, row in checkpoints.items()
                    if int(hashlib.sha256(cp.encode()).hexdigest(), 16) % args.worker_count == args.worker_index}
    # Checkpoints are assigned as units, so all diagnostic forks from one
    # checkpoint remain on exactly one worker and have one immutable initial answer.
    for cp_id, row in selected_cps.items():
        if cp_id in prior_cp:
            continue
        trace_id = "checkpoint_" + cp_id
        event_path = out / "checkpoint_traces" / trace_id / "events.jsonl"
        seq = 0
        started = time.monotonic()
        try:
            seq = emit(event_path, seq, trace_id, "RUN_START", "RUNNING",
                       {"checkpoint_id": cp_id, "case_id": row["case_id"], "group_id": row["group_id"],
                        "model_id": args.model_id, "public_only": True})
            messages = [{"role": "system", "content": system_prompt(row["group_id"])},
                        {"role": "user", "content": case_prompt(public[row["case_id"]])}]
            payload, seq = public_tool_loop(provider, messages, row["group_id"], limits, event_path, trace_id, seq, True)
            record = {"checkpoint_id": cp_id, "case_id": row["case_id"], "group_id": row["group_id"],
                      "initial_decision": payload["decision"], "checkpoint_payload": payload,
                      "trace_ref": str(event_path.relative_to(out)), "status": "completed",
                      "elapsed_seconds": round(time.monotonic() - started, 3), "public_only": True}
            append_jsonl(checkpoint_path, record)
            emit(event_path, seq, trace_id, "RUN_END", "COMPLETED", {"status": "completed"})
            prior_cp[cp_id] = record
        except Exception as exc:
            emit(event_path, seq, trace_id, "ERROR", "FAILED", {"error_type": type(exc).__name__, "error": str(exc)})
            emit(event_path, seq + 1, trace_id, "RUN_END", "FAILED", {"status": "provider_error"})
            append_jsonl(checkpoint_path, {"checkpoint_id": cp_id, "case_id": row["case_id"], "group_id": row["group_id"],
                                            "status": "provider_error", "trace_ref": str(event_path.relative_to(out))})
            continue
    rows_for_worker = [row for row in selected if row["checkpoint_id"] in selected_cps]
    for index, row in enumerate(rows_for_worker, 1):
        if row["run_id"] in prior_states and prior_states[row["run_id"]].get("status") == "completed":
            continue
        cp = prior_cp.get(row["checkpoint_id"])
        if not cp or cp.get("status") != "completed":
            state = {"run_id": row["run_id"], "checkpoint_id": row["checkpoint_id"], "status": "checkpoint_missing",
                     "trace_ref": cp.get("trace_ref") if cp else None, "injection_audit": {"applied_stages": row["inject_stages"]}}
            append_jsonl(state_path, state)
            prior_states[row["run_id"]] = state
            continue
        trace_id = row["run_id"]
        event_path = out / "traces" / trace_id / "events.jsonl"
        seq = 0
        injection: dict[str, Any] = {"applied_stages": row["inject_stages"]}
        try:
            seq = emit(event_path, seq, trace_id, "RUN_START", "RUNNING",
                       {"run_id": trace_id, "checkpoint_id": row["checkpoint_id"], "case_id": row["case_id"],
                        "diagnostic_arm": row["diagnostic_arm"], "group_id": row["group_id"], "public_only": True})
            case = public[row["case_id"]]
            label = labels[row["case_id"]]
            injection = injection_for(row, label)
            seq = emit(event_path, seq, trace_id, "INJECTION_APPLIED", "COMPLETED", injection)
            messages = [{"role": "system", "content": system_prompt(row["group_id"])},
                        {"role": "user", "content": case_prompt(case)},
                        {"role": "assistant", "content": json.dumps(cp["checkpoint_payload"], ensure_ascii=False)},
                        {"role": "user", "content": json.dumps({"diagnostic_arm": row["diagnostic_arm"],
                           "inject_stages": row["inject_stages"], "diagnostic_information": injection,
                           "instruction": "Re-evaluate the case with only these supplied diagnostic stages. Return the required JSON."}, ensure_ascii=False)}]
            payload, seq = public_tool_loop(provider, messages, row["group_id"], limits, event_path, trace_id, seq, False)
            stages = normalize_stages(payload)
            state = {"run_id": trace_id, "checkpoint_id": row["checkpoint_id"], "status": "completed",
                     "initial_decision": cp["initial_decision"], "final_decision": payload["decision"],
                     "stages": stages, "trace_ref": str(event_path.relative_to(out)),
                     "checkpoint_trace_ref": cp["trace_ref"], "injection_audit": injection,
                     "usage": {"model_calls": limits.model_calls, "tool_calls": limits.tool_calls,
                               "total_tokens": limits.total_tokens, "cost_usd": limits.cost_usd},
                     "public_only_checkpoint": True}
            append_jsonl(state_path, state)
            prior_states[trace_id] = state
            emit(event_path, seq, trace_id, "RUN_END", "COMPLETED", {"status": "completed"})
        except Exception as exc:
            emit(event_path, seq, trace_id, "ERROR", "FAILED", {"error_type": type(exc).__name__, "error": str(exc)})
            emit(event_path, seq + 1, trace_id, "RUN_END", "FAILED", {"status": "provider_error"})
            state = {"run_id": trace_id, "checkpoint_id": row["checkpoint_id"], "status": "provider_error",
                     "trace_ref": str(event_path.relative_to(out)), "injection_audit": injection if "injection" in locals() else {"applied_stages": row["inject_stages"]}}
            append_jsonl(state_path, state)
            prior_states[trace_id] = state
        if index % 10 == 0 or state.get("status") != "completed":
            print(f"G7 progress {index}/{len(rows_for_worker)}: {state.get('status')} calls={limits.model_calls} tools={limits.tool_calls} tokens={limits.total_tokens}", flush=True)
    summary = {"experiment_id": "g7_failure_localization", "worker_index": args.worker_index,
               "worker_count": args.worker_count, "plan_count": len(plan), "selected_rows": len(rows_for_worker),
               "states_count": len(readl(state_path)), "checkpoints_count": len(readl(checkpoint_path)),
               "limits": limits.__dict__, "model_id": args.model_id, "base_url": args.base_url,
               "public_sha256": sha256_file(args.public), "labels_sha256": sha256_file(args.labels),
               "plan_sha256": sha256_file(args.plan), "completed_at_utc": utc_now()}
    write_json(out / f"runner_summary.worker-{args.worker_count}-{args.worker_index}.json", summary)
    print(f"G7 RUN COMPLETE: states={summary['states_count']} checkpoints={summary['checkpoints_count']} worker={args.worker_index}/{args.worker_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
