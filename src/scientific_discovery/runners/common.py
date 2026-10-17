"""Shared runner helpers kept free of benchmark-specific truth."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from typing import Any

from ..benchmark.base import Observation
from ..environment.budget import BudgetLedger
from ..models.provider import LLMProvider, ProviderResponse
from ..utils.json_protocol import ProtocolError, canonical_json, parse_json_object


def observation_dict(observation: Observation) -> dict[str, Any]:
    return asdict(observation)


def freeze_plan(plan: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    frozen = json.loads(canonical_json(plan))
    encoded = canonical_json(frozen).encode("utf-8")
    return frozen, hashlib.sha256(encoded).hexdigest()


def validate_plan_shape(plan: Any, schema: dict[str, Any], max_experiments: int) -> list[dict[str, float]]:
    if not isinstance(plan, list):
        raise ProtocolError("experiments must be a list")
    if len(plan) > max_experiments:
        raise ProtocolError("planned experiments exceed the registered budget")
    required = set(schema.get("required", []))
    clean: list[dict[str, float]] = []
    for index, action in enumerate(plan):
        if not isinstance(action, dict) or set(action) != required:
            raise ProtocolError(f"experiment {index} does not match the action schema")
        item: dict[str, float] = {}
        for key, value in action.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ProtocolError(f"experiment {index} field {key} must be finite numeric")
            numeric = float(value)
            spec = schema.get("properties", {}).get(key, {})
            minimum = spec.get("minimum")
            if minimum is not None and (
                numeric <= minimum if spec.get("exclusiveMinimum") else numeric < minimum
            ):
                relation = ">" if spec.get("exclusiveMinimum") else ">="
                raise ProtocolError(f"experiment {index} field {key} must be {relation} {minimum}")
            maximum = spec.get("maximum")
            if maximum is not None and numeric > maximum:
                raise ProtocolError(f"experiment {index} field {key} must be <= {maximum}")
            item[key] = numeric
        clean.append(item)
    return clean


def record_provider_call(provider: LLMProvider, response: ProviderResponse, ledger: BudgetLedger) -> None:
    ledger.consume_api(response.usage.input_tokens, response.usage.output_tokens, response.usage.cost_usd)


def ensure_provider_call(ledger: BudgetLedger, provider: LLMProvider | None = None) -> None:
    """Check the ledger and tighten a provider's socket timeout to its budget.

    ``urllib`` cannot cancel an already-running request safely, but its socket
    timeout can be bounded before the request is sent.  Passing the remaining
    runtime to the provider prevents a late adaptive call from starting with
    the full configured timeout after the scientific run budget is nearly
    exhausted.  The post-request ledger snapshot still records any transport
    overrun truthfully.
    """

    ledger.ensure_api_slot()
    if provider is None:
        return
    # ``run_one`` decorates the concrete provider with policy and trace
    # wrappers.  Reach only through those local decorators; never inspect
    # arbitrary model state or make a hidden provider call.
    target = provider
    seen: set[int] = set()
    while not hasattr(target, "timeout") and hasattr(target, "provider") and id(target) not in seen:
        seen.add(id(target))
        target = getattr(target, "provider")
    if not hasattr(target, "timeout"):
        return
    remaining = float(ledger.remaining()["runtime_seconds"])
    configured = float(getattr(target, "timeout"))
    if remaining <= 0:
        raise RuntimeError("runtime budget exhausted before provider request")
    # Keep a small positive timeout for transports that reject zero.  The
    # ledger remains the authoritative gate; this is a best-effort transport
    # bound because socket timeouts are not process cancellation.
    setattr(target, "timeout", min(configured, max(0.1, remaining)))


def response_payload(response: ProviderResponse) -> dict[str, Any]:
    if response.tool_calls:
        call = response.tool_calls[0]
        function = call.get("function", call)
        arguments = function.get("arguments", function.get("parameters", {}))
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        return {"tool_call": function.get("name", "run_experiment"), "arguments": arguments}
    return parse_json_object(response.content)
