"""One-model provider adapter with append-only raw trace capture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.audit_repair.cost_ledger import CostLedger
from src.scientific_discovery.models.provider import OpenAICompatibleProvider

from .common import append_jsonl, read_jsonl


class SingleKimiProvider:
    def __init__(self, run: Path, key_file: Path, base_url: str, model_id: str, max_cost: float, timeout: float, max_output_tokens: int = 512) -> None:
        if model_id != "kimi-k2.5":
            raise ValueError("V9 permits only the single base model kimi-k2.5")
        key = key_file.read_text(encoding="utf-8").strip()
        if not key:
            raise ValueError("Kimi key file is empty")
        self.run = run
        self.raw = run / "logs" / "provider_traces.jsonl"
        self.raw.parent.mkdir(parents=True, exist_ok=True)
        self.raw.touch(exist_ok=True)
        self.ledger = CostLedger(run / "cost_ledger.sqlite", global_cap=200.0, g7_cap=60.0, worker_cap=max_cost)
        self.provider = OpenAICompatibleProvider(
            api_key=key, base_url=base_url, model_name=model_id, timeout=timeout,
            max_retries=0, input_cost_per_1k=0.001, output_cost_per_1k=0.003,
            max_cost_usd=max_cost, max_output_tokens=max_output_tokens, reservation_output_tokens=max_output_tokens,
            cost_ledger=self.ledger, ledger_scope="g7", ledger_worker="v9-single-kimi",
            ledger_ref_prefix="v9-single-kimi", require_cost_ledger=True,
        )
        self.call_no = 0
        for row in read_jsonl(self.raw):
            self.call_no = max(self.call_no, int(row.get("v9_call_number", 0) or 0))

    def call(self, protocol: str, unit_id: str, role: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.call_no += 1
        before = len(self.provider.audit_trace())
        content: str | None = None
        usage: dict[str, Any] = {}
        error: str | None = None
        try:
            response = self.provider.complete(messages)
            content = response.content
            usage = response.usage.__dict__ if response.usage is not None else {}
        except Exception as exc:  # preserve the failure and continue the cohort
            error = f"{type(exc).__name__}:{str(exc)[:500]}"
        traces = self.provider.audit_trace()[before:]
        if traces:
            for index, trace in enumerate(traces, 1):
                append_jsonl(self.raw, {
                    "v9_call_number": self.call_no, "protocol": protocol, "unit_id": unit_id,
                    "role": role, "trace_index": index, "model_id": "kimi-k2.5", "trace": trace,
                })
        else:
            append_jsonl(self.raw, {
                "v9_call_number": self.call_no, "protocol": protocol, "unit_id": unit_id,
                "role": role, "model_id": "kimi-k2.5", "error": error or "NO_PROVIDER_TRACE",
            })
        return {"content": content, "usage": usage, "error": error, "call_number": self.call_no}
