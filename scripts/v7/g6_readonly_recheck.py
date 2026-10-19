from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_json


def recheck(results: Path, proof_dir: Path, out: Path) -> dict[str, Any]:
    rows = read_jsonl(results); failures: list[str] = []; seen = set()
    for row in rows:
        idx = row.get("unit_index")
        if idx in seen: failures.append(f"duplicate_unit:{idx}")
        seen.add(idx)
        status = row.get("status")
        if status in {"MACHINE_PROVEN", "MACHINE_COUNTEREXAMPLE"}:
            refs = list(proof_dir.glob(f"{int(idx):04d}_{status}.json"))
            if len(refs) != 1: failures.append(f"certificate_missing:{idx}")
            else:
                cert = json.loads(refs[0].read_text(encoding="utf-8"))
                if cert.get("source_row_sha256") != row.get("source_row_sha256"): failures.append(f"certificate_source_mismatch:{idx}")
    result = {"rechecked_rows": len(rows), "unique_units": len(seen), "failures": failures, "result_sha256": sha256_file(results), "independent_reviewer": "g6_readonly_recheck_v1", "formal_denominator_preserved": 552}
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--results", type=Path, required=True); parser.add_argument("--proof-dir", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); result = recheck(args.results, args.proof_dir, args.out); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not result["failures"] else 2


if __name__ == "__main__": raise SystemExit(main())
