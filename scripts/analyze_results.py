"""Reproducible wrapper for result analysis and figure generation."""

from __future__ import annotations

import sys

from scientific_discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["analyze", *sys.argv[1:]]))
