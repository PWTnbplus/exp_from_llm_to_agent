#!/usr/bin/env python3
"""Create the auditable G8 public denominator from completed G7 checkpoints."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def index_unique(rows: list[dict], fields: tuple[str, ...], label: str) -> tuple[dict, list[str]]:
    indexed = {}
    errors: list[str] = []
    for line_number, row in enumerate(rows, 1):
        values = [row.get(field) for field in fields]
        if any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"{label}_missing_identity:{line_number}")
            continue
        key = values[0] if len(values) == 1 else tuple(values)
        if key in indexed:
            errors.append(f"{label}_duplicate_identity:{key!r}")
            continue
        indexed[key] = row
    return indexed, errors


def select_complete_families(
    public: list[dict], checkpoints: list[dict]
) -> tuple[list[dict], list[str], dict[str, int]]:
    """Select only families with four unique, completed public checkpoints."""
    public_by_case, public_errors = index_unique(public, ("case_id",), "public_case")
    checkpoint_by_pair, pair_errors = index_unique(checkpoints, ("case_id", "group_id"), "checkpoint_pair")
    _, checkpoint_id_errors = index_unique(checkpoints, ("checkpoint_id",), "checkpoint")
    errors = [*public_errors, *pair_errors, *checkpoint_id_errors]
    complete: dict[str, set[tuple[str, str]]] = {}
    excluded_statuses: collections.Counter[str] = collections.Counter()
    for row in checkpoints:
        case_id = row.get("case_id")
        if case_id not in public_by_case:
            errors.append(f"checkpoint_unknown_public_case:{case_id!r}")
            continue
        status = row.get("status")
        if status != "completed":
            excluded_statuses[str(status)] += 1
            continue
        public_row = public_by_case[case_id]
        family = public_row.get("theory_family_id")
        cf_type = public_row.get("cf_type")
        if cf_type not in {"CF1", "CF2"}:
            continue
        if not isinstance(family, str) or not family.strip():
            errors.append(f"public_case_missing_family_or_cf:{case_id!r}")
            continue
        complete.setdefault(family, set()).add((cf_type, row["group_id"]))
    families = sorted(
        family for family, pairs in complete.items()
        if pairs == {("CF1", "G3"), ("CF1", "G4"), ("CF2", "G3"), ("CF2", "G4")}
    )
    family_set = set(families)
    selected = [
        row for row in public
        if row.get("theory_family_id") in family_set and row.get("cf_type") in {"CF1", "CF2"}
    ]
    selected.sort(key=lambda row: row["case_id"])
    if not selected or len(selected) != len(families) * 2:
        errors.append(f"expected exactly two CF1/CF2 cases per complete family, got {len(selected)}")
    if errors:
        selected = []
    return selected, errors, dict(excluded_statuses)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--checkpoints", type=Path, required=True)
    p.add_argument("--out-public", type=Path, required=True)
    p.add_argument("--out-manifest", type=Path, required=True)
    args = p.parse_args()
    public = load(args.public)
    checkpoints = load(args.checkpoints)
    selected, errors, excluded_statuses = select_complete_families(public, checkpoints)
    if errors:
        raise SystemExit("G8 input validation failed: " + "; ".join(errors))
    families = sorted({row["theory_family_id"] for row in selected})
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
        "excluded_failures": "All G7 non-completed checkpoints remain excluded from this derived G8 input view and are not imputed.",
        "excluded_checkpoint_status_counts": excluded_statuses,
    }
    args.out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
