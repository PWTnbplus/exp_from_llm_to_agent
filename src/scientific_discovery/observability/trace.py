"""Unified JSONL trace recording without fabricating hidden model reasoning.

The recorder stores only observable inputs, outputs, tool interactions and
post-submission evaluation data.  It deliberately has no API for recording
inferred chain-of-thought or unobserved agent state.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import uuid
from typing import Any, Mapping

from ..models.provider import LLMProvider, ProviderResponse


EVENT_TYPES = frozenset({
    "RUN_START",
    "MODEL_INPUT",
    "MODEL_OUTPUT",
    "PROVIDER_ATTEMPT",
    "TOOL_CALL",
    "TOOL_RESULT",
    "PREDICTION",
    "HYPOTHESIS_UPDATE",
    "VERIFICATION",
    "EVALUATION",
    "POLICY_CHECK",
    "BUDGET",
    "ERROR",
    "RUN_END",
})

_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|authorization|access[_-]?token|client[_-]?secret|password|credential|secret|ground_truth|answer_key|verification_code|verification_status)",
    re.IGNORECASE,
)
_SECRET_TEXT = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+|\bsk-[A-Za-z0-9_-]{12,}")
_PRIVATE_TEXT = re.compile(r"(?i)ground_truth|answer_key|verification_code|verification_status")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(value: Any, *, key: str = "") -> Any:
    """Make a JSON-safe, recursively redacted snapshot of an event value."""

    if _SECRET_KEY.search(key):
        return "[REDACTED]"
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(k): _redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str):
            return _PRIVATE_TEXT.sub("[PRIVATE_FIELD]", _SECRET_TEXT.sub("[REDACTED]", value))
        return value
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


class TraceRecorder:
    """Thread-safe append-only JSONL recorder with durable per-event writes."""

    def __init__(
        self,
        path: Path,
        *,
        run_id: str | None = None,
        task_id: str = "",
        system_type: str = "unknown",
        model_name: str = "unknown",
        model_version: str = "unknown",
        experiment_id: str | None = None,
        durable: bool = True,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or uuid.uuid4().hex
        self.task_id = task_id
        self.system_type = system_type
        self.model_name = model_name
        self.model_version = model_version
        self.experiment_id = experiment_id or self.run_id
        self.durable = durable
        self._sequence = 0
        self._lock = threading.Lock()
        self._handle = self.path.open("a", encoding="utf-8", newline="\n")
        self._closed = False

    def emit(
        self,
        event_type: str,
        *,
        step_id: str | None = None,
        parent_step_id: str | None = None,
        input: Any = None,
        output: Any = None,
        prediction: Any = None,
        tool_name: str | None = None,
        tool_arguments: Any = None,
        tool_result: Any = None,
        token_usage: Mapping[str, Any] | None = None,
        latency_ms: float | None = None,
        cost: float | None = None,
        status: str = "OK",
        error_message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported trace event type: {event_type}")
        with self._lock:
            if self._closed:
                raise RuntimeError("trace recorder is closed")
            self._sequence += 1
            generated_step = step_id or f"{self.run_id}:step-{self._sequence:06d}"
            event = {
                "event_id": f"{self.run_id}:event-{self._sequence:06d}",
                "sequence": self._sequence,
                "run_id": self.run_id,
                "experiment_id": self.experiment_id,
                "task_id": self.task_id,
                "system_type": self.system_type,
                "model_name": self.model_name,
                "model_version": self.model_version,
                "step_id": generated_step,
                "parent_step_id": parent_step_id,
                "event_type": event_type,
                "timestamp": _timestamp(),
                "input": _redact(input),
                "output": _redact(output),
                "prediction": _redact(prediction),
                "tool_name": tool_name,
                "tool_arguments": _redact(tool_arguments),
                "tool_result": _redact(tool_result),
                "token_usage": _redact(dict(token_usage or {})),
                "latency_ms": latency_ms,
                "cost": cost,
                "status": status,
                "error_message": _redact(error_message),
                "metadata": _redact(dict(metadata or {})),
            }
            line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str)
            self._handle.write(line + "\n")
            self._handle.flush()
            if self.durable:
                os.fsync(self._handle.fileno())
            return event

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._handle.flush()
                if self.durable:
                    os.fsync(self._handle.fileno())
                self._handle.close()
                self._closed = True

    def __enter__(self) -> "TraceRecorder":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


class NullTraceRecorder:
    """No-op recorder used when a caller intentionally does not persist logs."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex
        self.path: Path | None = None
        self._sequence = 0

    def emit(self, event_type: str, **kwargs: Any) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported trace event type: {event_type}")
        self._sequence += 1
        return {"event_id": f"{self.run_id}:event-{self._sequence:06d}", "step_id": kwargs.get("step_id") or f"{self.run_id}:step-{self._sequence:06d}"}

    def close(self) -> None:
        return None


class TraceProvider(LLMProvider):
    """Provider decorator that records exact model-bound I/O and latency."""

    def __init__(self, provider: LLMProvider, recorder: TraceRecorder | NullTraceRecorder):
        self.provider = provider
        self.recorder = recorder
        self.model_name = getattr(provider, "model_name", "unknown")

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> ProviderResponse:
        request = {"messages": messages, "tools": tools}
        started = time.perf_counter()
        previous_trace_count = len(self.provider.audit_trace())
        input_event = self.recorder.emit(
            "MODEL_INPUT",
            input=request,
            status="RUNNING",
            metadata={"observable_only": True},
        )
        try:
            response = self.provider.complete(messages, tools=tools)
        except Exception as exc:
            self._record_provider_attempts(previous_trace_count, input_event["step_id"], tools)
            self.recorder.emit(
                "ERROR",
                parent_step_id=input_event["step_id"],
                input=request,
                latency_ms=(time.perf_counter() - started) * 1000.0,
                status="FAILED",
                error_message=str(exc),
                metadata={"error_type": "model", "exception": type(exc).__name__},
            )
            raise
        self._record_provider_attempts(previous_trace_count, input_event["step_id"], tools)
        self.recorder.emit(
            "MODEL_OUTPUT",
            parent_step_id=input_event["step_id"],
            output={"content": response.content, "tool_calls": response.tool_calls},
            token_usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            latency_ms=(time.perf_counter() - started) * 1000.0,
            cost=response.usage.cost_usd,
            status="COMPLETED",
            metadata=response.metadata,
        )
        return response

    def _record_provider_attempts(self, previous_count: int, parent_step_id: str, tools: Any) -> None:
        """Persist actual provider attempts, including failed retry attempts."""

        traces = self.provider.audit_trace()[previous_count:]
        for item in traces:
            response = item.get("response", {}) if isinstance(item, dict) else {}
            error = item.get("error") if isinstance(item, dict) else None
            self.recorder.emit(
                "PROVIDER_ATTEMPT",
                parent_step_id=parent_step_id,
                input={"attempt": item.get("attempt", 1), "tools": tools},
                output={"provider": item.get("model", self.model_name), "error": error, "has_response": bool(response)},
                token_usage=response.get("usage", {}) if isinstance(response, dict) else {},
                cost=(response.get("usage", {}) or {}).get("cost_usd") if isinstance(response, dict) else None,
                status="FAILED" if error else "COMPLETED",
                metadata={"observable_only": True, "provider_attempt": True},
            )

    def audit_trace(self) -> list[dict[str, Any]]:
        return self.provider.audit_trace()


def read_trace(path: Path, *, event_type: str | None = None, run_id: str | None = None) -> list[dict[str, Any]]:
    """Read a complete or partially written JSONL trace, tolerating a final torn line."""

    events: list[dict[str, Any]] = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event_type and event.get("event_type") != event_type:
                    continue
                if run_id and event.get("run_id") != run_id:
                    continue
                events.append(event)
    except OSError:
        return []
    return events
