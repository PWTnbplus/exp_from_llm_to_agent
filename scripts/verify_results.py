"""Validate reproduction artifacts without reading protected scientific data."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scientific_discovery.project.offline import validate_result
from scientific_discovery.project.registry import EXPERIMENT_IDS


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--experiment")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--input", type=Path, default=Path("results/engineering_smoke"))
    args = parser.parse_args()
    ids = EXPERIMENT_IDS if args.all else [args.experiment]
    errors: list[str] = []
    for experiment_id in ids:
        path = args.input / experiment_id.replace(".", "_") / "result.json"
        if not path.exists():
            errors.append(f"missing result: {path}")
            continue
        errors.extend(validate_result(path))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"verified {len(ids)} offline result artifact(s); no scientific claim made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
