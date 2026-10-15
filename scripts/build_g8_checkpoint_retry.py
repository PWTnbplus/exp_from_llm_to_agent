#!/usr/bin/env python3
"""Build a retry input containing only failed/missing G8 checkpoint pairs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--base-checkpoints", type=Path, required=True)
    p.add_argument("--combined", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    public = load(args.public)
    base = load(args.base_checkpoints)
    combined = load(args.combined)
    families = sorted({row["theory_family_id"] for row in public})
    pairs_done = {(row["case_id"], row["group_id"], int(row.get("replicate", 0)))
                  for row in combined if row.get("status") == "completed"}
    base_by_pair = {(row["case_id"], row["group_id"]): row for row in base if row.get("status") == "completed"}
    missing = []
    for family in families:
        for cf in ("CF1", "CF2"):
            for group in ("G3", "G4"):
                key = (f"{family}-{cf}", group)
                if key not in base_by_pair:
                    continue
                if any((key[0], key[1], rep) not in pairs_done for rep in (1, 2)):
                    missing.append(base_by_pair[key])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in missing), encoding="utf-8")
    print(json.dumps({"families": families, "retry_base_rows": len(missing),
                      "retry_replicate_jobs": len(missing) * 2}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
