#!/usr/bin/env python3
"""JSON-stdin G8 adapter implementing the real, sham, off and extra-think arms."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scientific_discovery.models.provider import OpenAICompatibleProvider
from scripts.run_g6_counterfactual import TOOLS, execute_tool, extract_json, parse_tool_args
from scripts.run_g7_failure_localization import Limits
from scripts.g8_public_v_verifier import VERSION, verify_public_case

DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}


def add_event(events: list[dict[str, Any]], event_type: str, payload: dict[str, Any] | None = None) -> None:
    events.append({"event_type": event_type, "status": "COMPLETED", "payload": payload or {}})


def parse_response(text: str) -> dict[str, Any]:
    obj = extract_json(text)
    if not isinstance(obj, dict):
        raise ValueError("provider response did not contain an object")
    decision = str(obj.get("decision", obj.get("final_decision", ""))).upper().strip()
    if decision not in DECISIONS:
        raise ValueError(f"invalid decision {decision!r}")
    obj["decision"] = decision
    return obj


def public_family(case_id: str) -> str:
    return case_id.split("-CF", 1)[0].replace("G6F-", "", 1)


def mechanism(request: dict[str, Any], arm: str) -> tuple[str | None, dict[str, Any] | None]:
    model_visible = dict(request["model_visible"])
    model_visible.setdefault("theory_family_id", public_family(request["case_id"]))
    if arm in {"B_G3_REAL_M", "E_G4_PLUS_M", "E_G4_BASE"}:
        return "real", verify_public_case(model_visible)
    if arm == "C_G3_SHAM_M":
        real = verify_public_case(model_visible)
        return "sham", {
            "mechanism_id": "V", "verifier_version": VERSION,
            "public_input_sha256": real["public_input_sha256"],
            "observable_public_parameters": {}, "intervention_numeric_tokens": [], "checks": [],
            "quality": {"status": "SHAM_SCHEMA_ONLY", "non_oracle": True,
                        "decision_label_emitted": False, "private_answer_loaded": False},
        }
    return None, None


def system_prompt(group: str) -> str:
    mode = "fixed G3 Tools+Iteration" if group == "G3" else "adaptive G4"
    return ("You are a real-provider participant in experiment g8_mechanism_causality, "
            f"profile theory_benchmark, workflow {mode}.\n"
            "Use only the public case, public tools, and explicitly supplied public mechanism output. "
            "Never access files, network, hidden answers, private oracles, prior responses, or answer keys. "
            "Return JSON with decision, affected_claim_ids, revised_claim, and supporting_evidence. "
            "decision must be MAINTAIN, REJECT, REVISE, or UNDETERMINED. Do not reveal hidden chain-of-thought.")


def loop(provider: OpenAICompatibleProvider, messages: list[dict[str, Any]], group: str,
         extra: bool, limits: Limits, events: list[dict[str, Any]]) -> dict[str, Any]:
    max_calls = 3 if extra and group == "G3" else (2 if group == "G3" else 8)
    result: dict[str, Any] | None = None
    for index in range(max_calls):
        if group == "G3" and index == 1:
            messages.append({"role": "user", "content": "Perform the fixed second synthesis pass. Return only the required JSON."})
        if extra and group == "G3" and index == 2:
            messages.append({"role": "user", "content": "Perform one additional generic consistency pass over the same public evidence, then return the required JSON."})
        limits.before_model()
        add_event(events, "MODEL_REQUEST", {"call_index": index + 1, "messages": messages, "tools": TOOLS})
        response = provider.complete(messages, tools=TOOLS)
        limits.consume(response)
        add_event(events, "MODEL_RESPONSE", {"call_index": index + 1, "content": response.content,
                                               "tool_calls": response.tool_calls, "usage": response.usage.__dict__})
        if response.tool_calls:
            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
            for call in response.tool_calls:
                fn = call.get("function", call)
                name = str(fn.get("name", ""))
                args = parse_tool_args(fn.get("arguments", {}))
                limits.before_tool()
                add_event(events, "TOOL_CALL", {"tool_name": name, "tool_arguments": args})
                try:
                    tool_result = execute_tool(name, args)
                    tool_status = "COMPLETED"
                except Exception as exc:
                    tool_result = {"error_type": type(exc).__name__, "error": str(exc)}
                    tool_status = "FAILED"
                add_event(events, "TOOL_RESULT", {"tool_name": name, "tool_result": tool_result, "status": tool_status})
                messages.append({"role": "tool", "tool_call_id": call.get("id", f"tool-{limits.tool_calls}"),
                                 "name": name, "content": json.dumps(tool_result, ensure_ascii=False)})
            continue
        result = parse_response(response.content)
        if group == "G3" and index == 0:
            continue
        if not extra or group != "G3" or index >= 2:
            break
    if result is None:
        raise ValueError("no final JSON response")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--key-file", type=Path, required=True)
    p.add_argument("--model-id", required=True)
    p.add_argument("--base-url", required=True)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--input-cost-per-1k", type=float, default=0.001)
    p.add_argument("--output-cost-per-1k", type=float, default=0.003)
    p.add_argument("--max-output-tokens", type=int, default=1024)
    args = p.parse_args()
    request = json.load(sys.stdin)
    cfg = request["limits"]
    limits = Limits(int(cfg["max_model_calls"]), int(cfg["max_tool_calls"]), int(cfg["max_total_tokens"]), float(cfg["max_cost_usd"]))
    provider = OpenAICompatibleProvider(api_key=args.key_file.read_text(encoding="utf-8").strip(), base_url=args.base_url,
        model_name=args.model_id, timeout=args.timeout, max_retries=0, input_cost_per_1k=args.input_cost_per_1k,
        output_cost_per_1k=args.output_cost_per_1k, max_cost_usd=float(cfg["max_cost_usd"]), max_output_tokens=args.max_output_tokens)
    messages = [dict(message) for message in request["public_messages"]]
    if messages and messages[0].get("role") == "system":
        messages[0] = {"role": "system", "content": system_prompt(request["group_id"])}
    events: list[dict[str, Any]] = []
    arm = request["arm_id"]
    kind, output = mechanism(request, arm)
    if kind == "real":
        add_event(events, "MECHANISM_INVOKED", {"mechanism_id": "V", "mode": "real", "verifier_version": VERSION})
        add_event(events, "MECHANISM_OUTPUT_ACCEPTED", {"mechanism_id": "V", "quality": output["quality"]})
        messages.append({"role": "user", "content": json.dumps({"public_mechanism": output,
                         "instruction": "Use this public computation evidence as input, but independently decide the case."}, ensure_ascii=False)})
    elif kind == "sham":
        add_event(events, "SHAM_MECHANISM_INVOKED", {"mechanism_id": "V", "mode": "schema_matched_placebo", "verifier_version": VERSION})
        add_event(events, "SHAM_PAYLOAD_MATCHED", {"mechanism_id": "V", "schema": "V1", "semantic_payload": "neutral"})
        messages.append({"role": "user", "content": json.dumps({"public_mechanism": output,
                         "instruction": "This schema-matched placebo contains no scientific evidence. Decide from the public case only."}, ensure_ascii=False)})
    elif arm in {"F_G4_NO_M", "F_G4_MINUS_M"}:
        add_event(events, "MECHANISM_DISABLED", {"mechanism_id": "V", "state_update": "disabled_before_downstream_read"})
    if arm == "D_G3_EXTRA_THINK":
        add_event(events, "EXTRA_THINK_APPLIED", {"mode": "generic_public_consistency_pass", "extra_model_call": True})
        messages.append({"role": "user", "content": "Use one additional generic consistency pass over the unchanged public evidence before finalizing."})
    try:
        result = loop(provider, messages, request["group_id"], arm == "D_G3_EXTRA_THINK", limits, events)
        status = "COMPLETED"
    except Exception as exc:
        result = {"decision": "UNDETERMINED", "affected_claim_ids": [], "revised_claim": None,
                  "supporting_evidence": "technical failure; no scientific conclusion", "error_type": type(exc).__name__}
        status = "TECHNICAL_FAILURE"
        add_event(events, "ADAPTER_ERROR", {"error_type": type(exc).__name__, "error": str(exc)})
    result.update({"run_id": request["run_id"], "status": status, "events": events,
                   "usage": {"total_tokens": limits.total_tokens, "model_calls": limits.model_calls,
                              "tool_calls": limits.tool_calls, "cost_usd": limits.cost_usd},
                   "budget_enforced": True, "actual_model_snapshot": request["model_snapshot"],
                   "model_visible_trace": {"public_messages": messages, "mechanism_id": "V",
                                           "mechanism_mode": kind or "off", "public_only": True},
                   "public_only": True})
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
