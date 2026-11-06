"""Fail-closed environment and public-boundary checks."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scientific_discovery.project.registry import EXPERIMENT_IDS, load_registry, topological_order


def main() -> int:
    root = ROOT
    registry = load_registry()
    print(json.dumps({"python": sys.version.split()[0], "experiments": len(registry), "ids": list(registry)}, ensure_ascii=False))
    if tuple(registry) != EXPERIMENT_IDS or set(topological_order(registry)) != set(EXPERIMENT_IDS):
        print("ERROR: registry is incomplete or has invalid dependencies")
        return 1
    tracked = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
    forbidden_tracked = [path for path in tracked if path.startswith(("api_key/", "secrets/", "credentials/", "private/", "runs/")) or path.endswith((".pem", ".key", ".p12", ".pfx"))]
    if forbidden_tracked:
        print(f"ERROR: tracked private paths detected ({len(forbidden_tracked)}); use the public-release allowlist before publishing")
        return 1
    print("environment check passed; paid provider execution remains disabled by default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
