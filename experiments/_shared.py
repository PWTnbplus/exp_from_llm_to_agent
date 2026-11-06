"""Small wrappers that keep one independent entrypoint per experiment."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scientific_discovery.project.cli import experiment_wrapper_main  # noqa: E402
from scientific_discovery.project.offline import validate_result  # noqa: E402


def run_cli(experiment_id: str) -> int:
    return experiment_wrapper_main(experiment_id)


def evaluate_cli(experiment_id: str) -> int:
    output = ROOT / "results" / "engineering_smoke" / experiment_id.replace(".", "_") / "result.json"
    errors = validate_result(output)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"{experiment_id}: offline artifact validated; scientific scoring requires the protected independent evaluator")
    return 0
