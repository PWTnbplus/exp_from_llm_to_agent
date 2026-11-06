"""Shared command implementations for the public experiment wrappers."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .offline import run_offline
from .registry import load_registry, topological_order


def run_experiments(experiment_ids: Sequence[str], output_root: Path, resume: bool = False, mode: str = "offline") -> int:
    registry = load_registry()
    unknown = [value for value in experiment_ids if value not in registry]
    if unknown:
        raise SystemExit(f"unknown experiment id(s): {', '.join(unknown)}")
    if mode != "offline":
        raise SystemExit("REAL_RUN_BLOCKED: public reproduction requires protected data, credentials, budget and explicit local authorization")
    for experiment_id in experiment_ids:
        result = run_offline(registry[experiment_id], output_root, resume=resume)
        print(f"{experiment_id}: {result['status']} -> {output_root / experiment_id.replace('.', '_') / 'result.json'}")
    return 0


def reproduce_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe G0-G13/G8.5 reproduction entry point")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--experiment", action="append", dest="experiments")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--output", type=Path, default=Path("results/engineering_smoke"))
    args = parser.parse_args(argv)
    registry = load_registry()
    ids = topological_order(registry) if args.all else args.experiments
    return run_experiments(ids, args.output, resume=args.resume, mode=args.mode)


def experiment_wrapper_main(experiment_id: str, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Safe reproduction wrapper for {experiment_id}")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--output", type=Path, default=Path("results/engineering_smoke"))
    args = parser.parse_args(argv)
    return run_experiments([experiment_id], args.output, resume=args.resume, mode=args.mode)
