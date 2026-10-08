"""Configurable providers with an auditable request/response surface."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
from typing import Any, Callable, Iterable
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class ProviderResponse:
    content: str
    usage: Usage = field(default_factory=Usage)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider:
    """Provider protocol implemented without exposing benchmark internals."""

    model_name = "unknown"

    def audit_trace(self) -> list[dict[str, Any]]:
        return []

    def complete(self, messages: list[dict[str, str]], *, tools: list[dict[str, Any]] | None = None) -> ProviderResponse:
        raise NotImplementedError


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split())) if text else 0


class MockLLMProvider(LLMProvider):
    """Deterministic provider for tests and the non-paid smoke experiment."""

    model_name = "mock-provider"

    def __init__(
        self,
        responses: Iterable[str | dict[str, Any]] | None = None,
        handler: Callable[[list[dict[str, Any]], list[dict[str, Any]] | None], str | dict[str, Any]] | None = None,
    ):
        self._responses = list(responses or [])
        self._handler = handler
        self.calls: list[dict[str, Any]] = []
        self.traces: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, str]], *, tools: list[dict[str, Any]] | None = None) -> ProviderResponse:
        request_record = {"messages": json.loads(json.dumps(messages)), "tools": json.loads(json.dumps(tools)) if tools else None}
        self.calls.append(request_record)
        if self._handler is not None:
            value = self._handler(request_record["messages"], request_record["tools"])
        elif self._responses:
            value = self._responses.pop(0)
        else:
            raise RuntimeError("MockLLMProvider response queue is empty")
        content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        usage = Usage(input_tokens=_estimate_tokens(json.dumps(messages)), output_tokens=_estimate_tokens(content))
        response = ProviderResponse(content=content, usage=usage, metadata={"provider": "mock", "model": self.model_name})
        self.traces.append({"call_index": len(self.traces), "model": self.model_name, "request": request_record, "response": {
            "content": response.content, "tool_calls": response.tool_calls, "usage": response.usage.__dict__, "metadata": response.metadata,
        }})
        return response

    def audit_trace(self) -> list[dict[str, Any]]:
        return json.loads(json.dumps(self.traces))


class OpenAICompatibleProvider(LLMProvider):
    """Small OpenAI-compatible chat-completions client.

    It intentionally accepts tools only when the caller supplies them.  The
    LLM-only runner never supplies tools, which is an enforceable API-level
    distinction rather than a prompt-only instruction.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        input_cost_per_1k: float | None = None,
        output_cost_per_1k: float | None = None,
        max_cost_usd: float | None = None,
        max_output_tokens: int | None = None,
    ):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model_name = model_name or os.getenv("LLM_MODEL", "")
        self.timeout = float(timeout if timeout is not None else os.getenv("LLM_TIMEOUT", "60"))
        # Scientific group policies set this explicitly. The safe default is
        # zero: transport retries are extra model calls and must never be an
        # invisible source of compute or cost.
        self.max_retries = int(max_retries if max_retries is not None else os.getenv("LLM_MAX_RETRIES", "0"))
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.input_cost_per_1k = float(input_cost_per_1k if input_cost_per_1k is not None else os.getenv("LLM_COST_PER_1K_INPUT_TOKENS", "0"))
        self.output_cost_per_1k = float(output_cost_per_1k if output_cost_per_1k is not None else os.getenv("LLM_COST_PER_1K_OUTPUT_TOKENS", "0"))
        configured_cap = os.getenv("LLM_MAX_COST_USD", "")
        self.max_cost_usd = max_cost_usd if max_cost_usd is not None else (float(configured_cap) if configured_cap else None)
        self.max_output_tokens = int(max_output_tokens if max_output_tokens is not None else os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048"))
        if self.max_cost_usd is not None and self.max_cost_usd <= 0:
            raise ValueError("max_cost_usd must be positive when configured")
        self._reserved_cost_usd = 0.0
        self.calls: list[dict[str, Any]] = []
        self.traces: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, str]], *, tools: list[dict[str, Any]] | None = None) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is not configured")
        if not self.model_name:
            raise RuntimeError("LLM_MODEL is not configured")
        if self.input_cost_per_1k <= 0 and self.output_cost_per_1k <= 0:
            raise RuntimeError(
                "LLM token pricing is not configured; set "
                "LLM_COST_PER_1K_INPUT_TOKENS and LLM_COST_PER_1K_OUTPUT_TOKENS "
                "before enabling a real API run"
            )
        payload: dict[str, Any] = {"model": self.model_name, "messages": messages, "max_tokens": self.max_output_tokens}
        if tools is not None:
            payload["tools"] = tools
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            estimated_input = _estimate_tokens(json.dumps(messages, ensure_ascii=False))
            worst_case = (estimated_input / 1000) * self.input_cost_per_1k + (self.max_output_tokens / 1000) * self.output_cost_per_1k
            if self.max_cost_usd is not None and self._reserved_cost_usd + worst_case > self.max_cost_usd:
                raise RuntimeError("hard cost cap would be exceeded before provider request")
            self._reserved_cost_usd += worst_case
            started = time.monotonic()
            try:
                req = urlrequest.Request(f"{self.base_url}/chat/completions", data=body, headers=headers, method="POST")
                with urlrequest.urlopen(req, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                latency = time.monotonic() - started
                choice = data["choices"][0]
                message = choice.get("message", {})
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls") or []
                usage_data = data.get("usage") or {}
                input_tokens = int(usage_data.get("prompt_tokens", _estimate_tokens(json.dumps(messages))))
                output_tokens = int(usage_data.get("completion_tokens", _estimate_tokens(content)))
                cost = (input_tokens / 1000) * self.input_cost_per_1k + (output_tokens / 1000) * self.output_cost_per_1k
                self.calls.append({"messages": messages, "tools": tools, "latency_seconds": latency, "attempt": attempt + 1})
                response = ProviderResponse(
                    content=content,
                    tool_calls=tool_calls,
                    usage=Usage(input_tokens, output_tokens, cost),
                    metadata={"provider": "openai-compatible", "model": self.model_name, "raw_id": data.get("id"), "attempt": attempt + 1, "latency_seconds": latency},
                )
                self.traces.append({"call_index": len(self.traces), "model": self.model_name, "request": {"messages": messages, "tools": tools}, "response": {
                    "content": content, "tool_calls": tool_calls, "usage": response.usage.__dict__, "metadata": response.metadata,
                }})
                return response
            except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                self.traces.append({
                    "call_index": len(self.traces),
                    "model": self.model_name,
                    "request": {"messages": messages, "tools": tools},
                    "attempt": attempt + 1,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                    "latency_seconds": time.monotonic() - started,
                })
                if attempt >= self.max_retries:
                    break
        raise RuntimeError(f"LLM provider request failed after retries: {last_error}") from last_error

    def audit_trace(self) -> list[dict[str, Any]]:
        return json.loads(json.dumps(self.traces))
