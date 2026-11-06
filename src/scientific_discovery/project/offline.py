"""Deterministic, no-provider reproduction artifacts for public CI."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any
import uuid

from .registry import ExperimentDefinition


def _git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _config_hash(definition: ExperimentDefinition) -> str:
    payload = json.dumps(definition.__dict__, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_offline(definition: ExperimentDefinition, output_root: Path, resume: bool = False) -> dict[str, Any]:
    """Write one deterministic engineering smoke result without API access."""
    output_dir = output_root / definition.experiment_id.replace(".", "_")
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "result.json"
    if result_path.exists():
        if not resume:
            raise FileExistsError(f"refusing to overwrite existing result: {result_path}; use --resume")
        return json.loads(result_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "schema_version": "engineering-smoke-v1",
        "experiment_id": definition.experiment_id,
        "run_id": f"offline-{definition.experiment_id.replace('.', '_')}-{uuid.uuid4().hex[:12]}",
        "mode": "offline",
        "mock": True,
        "model_id": "synthetic-demo",
        "created_at_utc": now,
        "code_commit": _git_commit(Path(__file__).resolve().parents[3]),
        "config_hash": _config_hash(definition),
        "status": "ENGINEERING_SMOKE_ONLY",
        "scientific_result": False,
        "events": [{"event": "offline_smoke", "experiment_id": definition.experiment_id, "timestamp": now}],
        "note": "Synthetic engineering artifact. It is not a real scientific result and must not enter paper statistics.",
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def validate_result(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: {exc}"]
    for field in ("schema_version", "experiment_id", "run_id", "mode", "mock", "status", "scientific_result"):
        if field not in payload:
            errors.append(f"{path}: missing {field}")
    if payload.get("mode") == "offline" and payload.get("scientific_result") is not False:
        errors.append(f"{path}: offline artifacts must not claim scientific_result=true")
    return errors
