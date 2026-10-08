"""Provider-facing G1-G5 runners for the answer-separated theory benchmark."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import time
import uuid

import sympy as sp

from ..environment.budget import BudgetLedger, BudgetLimits
from ..experiment.policy import BoundedMemory, PolicyController, PolicyProvider, get_group_policy
from ..models.provider import LLMProvider
from ..observability.trace import NullTraceRecorder, TraceProvider, TraceRecorder
from .contamination import assert_public_task_safe, contamination_manifest
from .schema import load_public_benchmark
from .verification import verify_candidate


MODE_TO_GROUP = {
    "G1": "G1", "G2": "G2", "G3": "G3", "G4": "G4", "G5": "G5",
    "g1": "G1", "g2": "G2", "g3": "G3", "g4": "G4", "g5": "G5",
    "llm_only": "G1", "llm_tools": "G2", "iterative_reflection": "G3", "agent": "G4",
}
MODES = tuple(MODE_TO_GROUP)

_CALCULATOR = [{
    "type": "function",
    "function": {
        "name": "calculate_expression",
        "description": "Evaluate a finite symbolic expression using only supplied numeric substitutions.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string"}, "values": {"type": "object"}},
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
}]


def _json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("provider response must be a JSON object")
    return value


def _public_prompt(task: dict[str, Any], group: str) -> list[dict[str, str]]:
    assert_public_task_safe(task)
    return [
        {"role": "system", "content": (
            f"你是理论科学推理 benchmark 的 {group} 被测系统。只使用公开题面，不访问答案键、隐藏验证数据、网络、检索或文件系统。"
            "返回 JSON：{task_id, final_answer, derivation, assumptions, verification_notes}。"
        )},
        {"role": "user", "content": json.dumps({"group": group, "task": task}, ensure_ascii=False)},
    ]


def _tool_result(arguments: Any) -> str:
    if not isinstance(arguments, dict) or not isinstance(arguments.get("expression"), str):
        return json.dumps({"error": "expression is required"}, ensure_ascii=False)
    try:
        values = arguments.get("values") or {}
        if not isinstance(values, dict):
            raise ValueError("values must be an object")
        symbols = {str(k): sp.Float(v) for k, v in values.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        expr = sp.sympify(arguments["expression"], locals=symbols)
        if expr.free_symbols:
            return json.dumps({"expression": str(expr), "unresolved_symbols": sorted(str(x) for x in expr.free_symbols)}, ensure_ascii=False)
        return json.dumps({"value": float(expr.evalf())}, ensure_ascii=False)
    except (TypeError, ValueError, SyntaxError, sp.SympifyError) as exc:
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False)


def _complete_agent(provider: LLMProvider, messages: list[dict[str, Any]], *, controller: PolicyController, max_calls: int, trace: TraceRecorder | NullTraceRecorder, memory: BoundedMemory | None = None) -> tuple[dict[str, Any], int]:
    """Run a bounded tool loop; every model and compute step passes a gate."""

    calls = 0
    for _ in range(max_calls):
        calls += 1
        response = provider.complete(messages, tools=_CALCULATOR)
        if response.tool_calls:
            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
            for tool_call in response.tool_calls:
                function = tool_call.get("function", tool_call)
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                tool_name = str(function.get("name", "calculate_expression"))
                controller.before_tool_call(tool_name, compute=True)
                call_event = trace.emit("TOOL_CALL", input=arguments, tool_name=tool_name, tool_arguments=arguments, status="RUNNING", metadata={"authorized_tool": True})
                started = time.perf_counter()
                tool_content = _tool_result(arguments) if tool_name == "calculate_expression" else json.dumps({"error": "unsupported theory tool"})
                try:
                    tool_output = json.loads(tool_content)
                except json.JSONDecodeError:
                    tool_output = tool_content
                failed = isinstance(tool_output, dict) and "error" in tool_output
                trace.emit("TOOL_RESULT", parent_step_id=call_event["step_id"], output=tool_output, tool_name=tool_name, tool_arguments=arguments, tool_result=tool_output, latency_ms=(time.perf_counter() - started) * 1000.0, status="FAILED" if failed else "COMPLETED", metadata={"error_type": "tool"} if failed else {"compute_step": True})
                if memory is not None:
                    memory.write({"tool": tool_name, "result": tool_output})
                messages.append({"role": "tool", "tool_call_id": tool_call.get("id", "calculate"), "name": tool_name, "content": tool_content})
            continue
        return _json_content(response.content), calls
    raise RuntimeError("agent call budget exhausted before final JSON")


def run_task(task_id: str, provider: LLMProvider, mode: str, *, data_dir: Path | None = None, output_dir: Path | None = None, max_calls: int | None = None, group: str | None = None) -> dict[str, Any]:
    group_id = MODE_TO_GROUP.get(group or mode, (group or mode).upper())
    policy = get_group_policy(group_id)
    public_tasks, manifest = load_public_benchmark(data_dir)
    task = next((row for row in public_tasks if row["task_id"] == task_id), None)
    if task is None:
        raise ValueError(f"unknown task: {task_id}")
    assert_public_task_safe(task)
    contamination = contamination_manifest(public_tasks, version=str(manifest["version"]))
    started = datetime.now(timezone.utc).isoformat()
    run_id = uuid.uuid4().hex
    trace_path = Path(output_dir) / "logs" / f"{run_id}.jsonl" if output_dir is not None else None
    trace = TraceRecorder(trace_path, run_id=run_id, task_id=task_id, system_type=group_id, model_name=str(getattr(provider, "model_name", "unknown")), model_version=str(getattr(provider, "model_name", "unknown"))) if trace_path else NullTraceRecorder(run_id)
    trace.emit("RUN_START", input={"task": task}, status="RUNNING", metadata={"group": group_id, "group_policy": policy.as_dict(), "observable_only": True, "contamination_stratum": contamination["task_strata"][task_id]})
    controller = PolicyController(policy, trace=trace)
    ledger = BudgetLedger(BudgetLimits(max_experiments=policy.max_experiments, max_api_calls=policy.max_api_calls, max_input_tokens=policy.max_input_tokens, max_output_tokens=policy.max_output_tokens, max_cost_usd=float(getattr(provider, "max_cost_usd", 0.0) or 0.0)))
    guarded_provider = PolicyProvider(provider, controller)
    traced_provider = TraceProvider(guarded_provider, trace)
    protocol_valid = True
    calls = 0
    payload: dict[str, Any] = {}
    validation: dict[str, Any] = {"status": "MODEL_ERROR", "task_id": task_id, "answer_correct": False, "errors": ["model did not submit an answer"]}
    status = "FAILED"
    try:
        messages = _public_prompt(task, group_id)
        if group_id == "G1":
            ledger.ensure_api_slot()
            response = traced_provider.complete(messages, tools=None)
            calls = 1
            payload = _json_content(response.content)
        elif group_id == "G2":
            limit = min(max_calls or policy.max_model_calls, policy.max_model_calls)
            payload, calls = _complete_agent(traced_provider, messages, controller=controller, max_calls=limit, trace=trace)
        elif group_id == "G3":
            ledger.ensure_api_slot()
            draft = traced_provider.complete(messages, tools=None)
            messages += [{"role": "assistant", "content": draft.content}, {"role": "user", "content": "请只根据题面逐项检查刚才的答案，然后返回最终 JSON。"}]
            ledger.ensure_api_slot()
            final = traced_provider.complete(messages, tools=None)
            calls = 2
            payload = _json_content(final.content)
        else:
            limit = min(max_calls or policy.max_model_calls, policy.max_model_calls)
            memory = BoundedMemory(controller) if group_id == "G5" else None
            payload, calls = _complete_agent(traced_provider, messages, controller=controller, max_calls=limit, trace=trace, memory=memory)
        trace.emit("PREDICTION", prediction=payload.get("final_answer", payload), output=payload, status="COMPLETED", metadata={"source": "model_output"})
        validation = verify_candidate(task_id, payload, data_dir=data_dir, redact_errors=True)
        status = "COMPLETED" if validation["status"] != "VALIDATOR_ERROR" else "FAILED"
        trace.emit("EVALUATION", input={"prediction": payload}, output=validation, prediction=payload.get("final_answer", payload), status="COMPLETED" if validation.get("answer_correct", False) else "INCORRECT", metadata={"ground_truth_exposed_to_model": False, "private_evaluator": True, "evaluator": "structured-numeric-sympy-v1"})
    except Exception as exc:
        payload = {"error": f"{type(exc).__name__}: {exc}"}
        validation = {"status": "MODEL_ERROR", "task_id": task_id, "answer_correct": False, "errors": [type(exc).__name__]}
        protocol_valid = False
        trace.emit("ERROR", status="FAILED", error_message=str(exc), metadata={"error_type": "model_or_policy", "exception": type(exc).__name__})
    finally:
        for item in provider.audit_trace():
            usage = item.get("response", {}).get("usage", {})
            if usage:
                try:
                    ledger.consume_api(int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)), float(usage.get("cost_usd", 0.0)))
                except Exception as exc:
                    controller.violations.append(f"budget accounting: {type(exc).__name__}")
                    trace.emit("ERROR", status="FAILED", error_message=str(exc), metadata={"error_type": "budget_accounting", "exception": type(exc).__name__})
        trace.emit("BUDGET", output={"ledger": ledger.snapshot(), "policy": controller.snapshot()}, status="COMPLETED" if not controller.violations else "VIOLATION")
        trace.emit("RUN_END", output={"status": status, "validation": validation}, status=status, metadata={"group": group_id, "provider_calls": calls})
        trace.close()
    provider_trace = traced_provider.audit_trace()
    input_tokens = sum(int(item.get("response", {}).get("usage", {}).get("input_tokens", 0)) for item in provider_trace)
    output_tokens = sum(int(item.get("response", {}).get("usage", {}).get("output_tokens", 0)) for item in provider_trace)
    cost_usd = sum(float(item.get("response", {}).get("usage", {}).get("cost_usd", 0.0)) for item in provider_trace)
    result = {"task_id": task_id, "runner": group_id, "mode": mode, "group": group_id, "model_id": getattr(provider, "model_name", "unknown"), "status": status, "protocol_valid": protocol_valid, "evaluator_valid": validation["status"] != "VALIDATOR_ERROR", "mock": getattr(provider, "model_name", "") == "mock-provider", "answer": payload, "task": task, "validation": validation, "run_id": run_id, "trace_path": str(Path("logs") / f"{run_id}.jsonl") if trace_path else None, "metadata": {"started_at": started, "provider_calls": calls, "provider_trace": provider_trace, "policy": controller.snapshot(), "budget": {"used": {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost_usd}}}}
    if output_dir is not None:
        folder = Path(output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{group_id}__{task_id.replace(':', '__')}__{run_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return result
