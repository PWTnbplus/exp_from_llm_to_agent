"""Convenience wrapper; use `python scripts/smoke_test.py` from the project root."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scientific_discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["smoke-test"]))
