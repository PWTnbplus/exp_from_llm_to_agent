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
            item[key] = float(value)
        clean.append(item)
    return clean


def record_provider_call(provider: LLMProvider, response: ProviderResponse, ledger: BudgetLedger) -> None:
    ledger.consume_api(response.usage.input_tokens, response.usage.output_tokens, response.usage.cost_usd)


def ensure_provider_call(ledger: BudgetLedger) -> None:
    ledger.ensure_api_slot()


def response_payload(response: ProviderResponse) -> dict[str, Any]:
    if response.tool_calls:
        call = response.tool_calls[0]
        function = call.get("function", call)
        arguments = function.get("arguments", function.get("parameters", {}))
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        return {"tool_call": function.get("name", "run_experiment"), "arguments": arguments}
    return parse_json_object(response.content)
