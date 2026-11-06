"""Reproducible wrapper for the manifest-driven pilot command."""

from __future__ import annotations

import sys

from scientific_discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["pilot", *sys.argv[1:]]))
