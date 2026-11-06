"""One auditable resource ledger shared by both experimental arms."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import time
from typing import Any


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetLimits:
    max_experiments: int = 6
    max_measurements: int = 120
    max_api_calls: int = 20
    max_input_tokens: int = 100_000
    max_output_tokens: int = 30_000
    max_cost_usd: float = 0.0
    max_runtime_seconds: float = 3_600.0


class BudgetLedger:
    def __init__(self, limits: BudgetLimits):
        self.limits = limits
        self.experiments = 0
        self.measurements = 0
        self.api_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_usd = 0.0
        self.started_at = time.monotonic()
        self.closed = False

    def _check_runtime(self) -> None:
        if time.monotonic() - self.started_at > self.limits.max_runtime_seconds:
            raise BudgetExceeded("runtime budget exceeded")

    def consume_api(self, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        self._check_runtime()
        if self.api_calls + 1 > self.limits.max_api_calls:
            raise BudgetExceeded("API call budget exceeded")
        if self.input_tokens + input_tokens > self.limits.max_input_tokens:
            raise BudgetExceeded("input token budget exceeded")
        if self.output_tokens + output_tokens > self.limits.max_output_tokens:
            raise BudgetExceeded("output token budget exceeded")
        if self.cost_usd + cost_usd > self.limits.max_cost_usd and self.limits.max_cost_usd >= 0:
            raise BudgetExceeded("cost budget exceeded")
        self.api_calls += 1
        self.input_tokens += int(input_tokens)
        self.output_tokens += int(output_tokens)
        self.cost_usd += float(cost_usd)

    def ensure_api_slot(self) -> None:
        """Check the hard call-count gate before an external request is sent."""
        self._check_runtime()
        if self.api_calls + 1 > self.limits.max_api_calls:
            raise BudgetExceeded("API call budget exceeded before provider request")

    def consume_experiment(self, measurement_count: int = 1) -> None:
        self._check_runtime()
        if self.experiments + 1 > self.limits.max_experiments:
            raise BudgetExceeded("experiment budget exceeded")
        if self.measurements + measurement_count > self.limits.max_measurements:
            raise BudgetExceeded("measurement budget exceeded")
        self.experiments += 1
        self.measurements += int(measurement_count)

    def add_measurements(self, count: int) -> None:
        if self.measurements + count > self.limits.max_measurements:
            raise BudgetExceeded("measurement budget exceeded")
        self.measurements += int(count)

    def remaining(self) -> dict[str, int | float]:
        elapsed = time.monotonic() - self.started_at
        return {
            "experiments": max(0, self.limits.max_experiments - self.experiments),
            "measurements": max(0, self.limits.max_measurements - self.measurements),
            "api_calls": max(0, self.limits.max_api_calls - self.api_calls),
            "input_tokens": max(0, self.limits.max_input_tokens - self.input_tokens),
            "output_tokens": max(0, self.limits.max_output_tokens - self.output_tokens),
            "cost_usd": max(0.0, self.limits.max_cost_usd - self.cost_usd),
            "runtime_seconds": max(0.0, self.limits.max_runtime_seconds - elapsed),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "limits": asdict(self.limits),
            "used": {
                "experiments": self.experiments,
                "measurements": self.measurements,
                "api_calls": self.api_calls,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cost_usd": self.cost_usd,
                "runtime_seconds": time.monotonic() - self.started_at,
            },
            "remaining": self.remaining(),
        }
