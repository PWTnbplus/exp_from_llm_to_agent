from __future__ import annotations

from typing import Any


def verify(_ir: dict[str, Any]) -> dict[str, Any]:
    return {"verifier": "interval-safety-v1", "result": "UNKNOWN", "reason": "interval_backend_not_required_for_unparsed_historical_claim"}
