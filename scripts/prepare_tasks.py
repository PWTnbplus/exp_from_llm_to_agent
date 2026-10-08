"""Convenience wrapper for deterministic task-manifest generation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scientific_discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["prepare"]))
