"""Task-level metrics with explicit denominators."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def vldr(results: Iterable[dict[str, Any]]) -> float:
    rows = list(results)
    if not rows:
        return float("nan")
    return sum(bool(row.get("validated_success")) for row in rows) / len(rows)


def summarize_by(results: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        groups[row.get(key)].append(row)
    return [{key: group_key, "n": len(rows), "vldr": vldr(rows)} for group_key, rows in sorted(groups.items(), key=lambda item: str(item[0]))]


def paired_delta(rows: Iterable[dict[str, Any]]) -> dict[str, float | int]:
    rows = list(rows)
    pairs = [row for row in rows if row.get("agent") is not None and row.get("llm_only") is not None]
    deltas = [int(bool(row["agent"])) - int(bool(row["llm_only"])) for row in pairs]
    return {"n_pairs": len(deltas), "mean_delta": sum(deltas) / len(deltas) if deltas else float("nan")}
