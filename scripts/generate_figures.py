"""Regenerate figures when the private/local figure package is available."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", required=True)
    args = parser.parse_args()
    if not args.all:
        return 2
    root = Path(__file__).resolve().parents[1]
    generator = root / "paper_figures" / "regenerate_all.py"
    if not generator.exists():
        print("FIGURE_GENERATION_BLOCKED: private/local figure inputs are not part of the public package")
        return 2
    return subprocess.call([sys.executable, "-X", "utf8", str(generator)], cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
