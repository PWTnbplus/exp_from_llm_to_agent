from __future__ import annotations

from typing import Any


def verify(_ir: dict[str, Any]) -> dict[str, Any]:
    return {"verifier": "ode-certificate-v1", "result": "UNKNOWN", "reason": "no_ode_claim_in_historical_g6_public_audit"}
