#!/usr/bin/env python3
"""Create the auditable G8 public denominator from completed G7 checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--checkpoints", type=Path, required=True)
    p.add_argument("--out-public", type=Path, required=True)
    p.add_argument("--out-manifest", type=Path, required=True)
    args = p.parse_args()
    public = load(args.public)
    checkpoints = load(args.checkpoints)
    complete = defaultdict(set)
    for row in checkpoints:
        suffix = row["case_id"].split("-CF", 1)[1]
        complete[row["case_id"].split("-CF", 1)[0]].add(("CF" + suffix, row["group_id"]))
    families = sorted(family for family, pairs in complete.items() if pairs == {("CF1", "G3"), ("CF1", "G4"), ("CF2", "G3"), ("CF2", "G4")})
    selected = [row for row in public if row.get("theory_family_id") in set(families) and row.get("cf_type") in {"CF1", "CF2"}]
    selected.sort(key=lambda row: row["case_id"])
    if not selected or len(selected) != len(families) * 2:
        raise SystemExit(f"expected exactly two CF1/CF2 cases per complete family, got {len(selected)}")
    args.out_public.parent.mkdir(parents=True, exist_ok=True)
    args.out_public.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in selected), encoding="utf-8")
    manifest = {
        "purpose": "G8 reduced formal denominator after preserving G7 checkpoint failures",
        "source_public": str(args.public.resolve()),
        "source_public_sha256": sha(args.public),
        "source_checkpoints": str(args.checkpoints.resolve()),
        "source_checkpoints_sha256": sha(args.checkpoints),
        "selected_theory_families": families,
        "n_families": len(families),
        "n_cases": len(selected),
        "cf_types": ["CF1", "CF2"],
        "selection_rule": "retain only families with completed real G7 public checkpoints for both groups and both CF1/CF2; no outcome labels used",
        "excluded_failures": "All G7 provider-error checkpoints remain excluded from this derived G8 input view and are not imputed.",
    }
    args.out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
