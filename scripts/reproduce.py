"""Unified reproduction CLI; defaults to deterministic offline smoke artifacts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scientific_discovery.project.cli import reproduce_main


if __name__ == "__main__":
    raise SystemExit(reproduce_main())
