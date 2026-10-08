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
