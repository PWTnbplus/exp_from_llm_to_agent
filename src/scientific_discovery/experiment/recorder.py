"""Append-only JSON result persistence with no secrets."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from ..benchmark.base import RunResult


def serialize_run(result: RunResult) -> dict[str, Any]:
    return asdict(result)


class ResultRecorder:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, result: RunResult, validation: dict[str, Any] | None = None) -> Path:
        payload = serialize_run(result)
        if validation is not None:
            payload["validation"] = validation
        path = self.output_dir / f"{result.runner}_{result.task_id.replace(':', '__')}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path
