"""Reproducible wrapper for one controlled experiment."""

from __future__ import annotations

import sys

from scientific_discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["run", *sys.argv[1:]]))
