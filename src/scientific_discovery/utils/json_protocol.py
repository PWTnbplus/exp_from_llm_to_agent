"""Strict, dependency-free JSON response handling."""

from __future__ import annotations

import json
from typing import Any


class ProtocolError(ValueError):
    pass


def parse_json_object(content: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(content, dict):
        value = content
    else:
        text = str(content).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].lstrip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"response is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProtocolError("response must be a JSON object")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
