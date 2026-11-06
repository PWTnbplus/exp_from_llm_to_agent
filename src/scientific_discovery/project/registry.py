"""Load the auditable G0--G13/G8.5 experiment registry.

The checked-in registry is JSON syntax stored in a ``.yaml`` file. JSON is a
valid YAML subset, so this public layer has no PyYAML dependency and remains
deterministic in offline CI.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "configs" / "experiment_registry.yaml"
EXPERIMENT_IDS = (
    "G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G8.5",
    "G9", "G10", "G11", "G12", "G13",
)


@dataclass(frozen=True)
class ExperimentDefinition:
    experiment_id: str
    scientific_question: str
    description: str
    dependencies: tuple[str, ...]
    implementation_status: str
    tested_status: str
    real_executed_status: str
    reproducibility_status: str
    legacy_entrypoints: tuple[str, ...]
    data_boundary: str


def _read_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("experiments"), list):
        raise ValueError(f"invalid experiment registry: {path}")
    return payload


def load_registry(path: Path | None = None) -> dict[str, ExperimentDefinition]:
    raw = _read_registry(path or REGISTRY_PATH)
    definitions: dict[str, ExperimentDefinition] = {}
    for item in raw["experiments"]:
        definition = ExperimentDefinition(
            experiment_id=str(item["experiment_id"]),
            scientific_question=str(item["scientific_question"]),
            description=str(item["description"]),
            dependencies=tuple(str(value) for value in item.get("dependencies", [])),
            implementation_status=str(item["status"]["IMPLEMENTED"]),
            tested_status=str(item["status"]["TESTED"]),
            real_executed_status=str(item["status"]["REAL_EXECUTED"]),
            reproducibility_status=str(item["status"]["REPRODUCIBLE"]),
            legacy_entrypoints=tuple(str(value) for value in item.get("legacy_entrypoints", [])),
            data_boundary=str(item["data_boundary"]),
        )
        if definition.experiment_id in definitions:
            raise ValueError(f"duplicate experiment id: {definition.experiment_id}")
        definitions[definition.experiment_id] = definition
    if tuple(definitions) != EXPERIMENT_IDS:
        raise ValueError(f"registry ids must be ordered as {EXPERIMENT_IDS}")
    return definitions


def topological_order(registry: dict[str, ExperimentDefinition]) -> list[str]:
    """Return dependency order and fail closed on cycles or unknown inputs."""
    remaining = {key: set(value.dependencies) for key, value in registry.items()}
    order: list[str] = []
    while remaining:
        ready = [key for key, deps in remaining.items() if not deps]
        if not ready:
            raise ValueError("experiment registry contains a dependency cycle")
        for key in sorted(ready, key=EXPERIMENT_IDS.index):
            order.append(key)
            remaining.pop(key)
            for deps in remaining.values():
                deps.discard(key)
    return order
