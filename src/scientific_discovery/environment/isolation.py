"""Data-boundary helpers used when crossing into model context."""

from __future__ import annotations

import copy
import json
from typing import Any


def json_safe_copy(value: Any) -> Any:
    """Copy numpy scalars/arrays and other JSON-compatible simulator output."""

    try:
        return json.loads(json.dumps(value, default=lambda x: x.item() if hasattr(x, "item") else list(x)))
    except (TypeError, ValueError):
        return copy.deepcopy(value)


def assert_public_text(text: str) -> None:
    """Reject obvious hidden-source/evaluator material before model dispatch."""

    forbidden = (
        "HIDDEN_CONSTANT",
        "ground_truth_law",
        "ground_truth",
        "answer_key",
        "verification_code",
        "verification_status",
        "Validation targets",
        "evaluation_results",
        "modules/",
        "laws.py",
    )
    lowered = text.lower()
    for token in forbidden:
        if token.lower() in lowered:
            raise AssertionError(f"hidden benchmark token leaked into model context: {token}")
