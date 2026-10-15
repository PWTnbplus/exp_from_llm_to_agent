"""Append-only JSON result persistence with no secrets."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any
import uuid

from ..benchmark.base import RunResult


def serialize_run(result: RunResult) -> dict[str, Any]:
    return asdict(result)


_PRIVATE_RESULT_KEYS = frozenset({
    "ground_truth",
    "answer_key",
    "private_oracle",
    "g6_private_oracle",
    "verification_code",
})


def _public_result_value(value: Any) -> Any:
    """Remove hidden evaluator payloads before writing ordinary result files."""

    if isinstance(value, dict):
        return {
            str(key): _public_result_value(item)
            for key, item in value.items()
            if str(key).lower() not in _PRIVATE_RESULT_KEYS
        }
    if isinstance(value, list):
        return [_public_result_value(item) for item in value]
    if isinstance(value, tuple):
        return [_public_result_value(item) for item in value]
    return value


class ResultRecorder:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        result: RunResult,
        validation: dict[str, Any] | None = None,
        *,
        replicate_index: int | None = None,
    ) -> Path:
        payload = serialize_run(result)
        if validation is not None:
            payload["validation"] = validation
        payload = _public_result_value(payload)
        stem = f"{result.runner}_{result.task_id.replace(':', '__')}"
        if replicate_index is not None:
            stem += f"__replicate-{int(replicate_index):03d}"
            path = self.output_dir / f"{stem}.json"
            if path.exists():
                raise FileExistsError(f"result already exists: {path}")
        elif result.run_id:
            path = self.output_dir / f"{stem}__{result.run_id}.json"
        else:
            path = self.output_dir / f"{stem}.json"
            if path.exists():
                path = self.output_dir / f"{stem}__{uuid.uuid4().hex}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path
