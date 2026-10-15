#!/usr/bin/env python3
"""Merge G8 checkpoint views without silently retaining provider errors."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--primary", type=Path, required=True)
    p.add_argument("--retry", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    public = load(args.public)
    base = load(args.base)
    primary = load(args.primary)
    retry = load(args.retry)
    merged = {}
    for source in (base, primary, retry):
        for row in source:
            if row.get("status") == "completed":
                key = (row["case_id"], row["group_id"], int(row.get("replicate", 0)))
                merged.setdefault(key, row)
    families = sorted({row["theory_family_id"] for row in public})
    expected = {(f"{family}-CF{cf}", group, rep)
                for family in families for cf in (1, 2) for group in ("G3", "G4") for rep in (0, 1, 2)}
    missing = sorted(expected - set(merged))
    result = [merged[key] for key in sorted(merged)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in result), encoding="utf-8")
    manifest = {"base_sha256": sha(args.base), "primary_sha256": sha(args.primary), "retry_sha256": sha(args.retry),
                "public_sha256": sha(args.public), "families": families, "completed_rows": len(result),
                "expected_rows": len(expected), "missing": missing,
                "provider_error_rows_not_merged": len([row for row in primary + retry if row.get("status") != "completed"]),
                "selection_rule": "completed rows only; first completed row wins by (case,group,replicate); failures remain in source directories"}
    (args.out.parent / "g8_checkpoint_merge_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if not missing else 2


if __name__ == "__main__":
    main()
