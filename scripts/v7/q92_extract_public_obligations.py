from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json


def extract(source: Path, out: Path) -> dict[str, Any]:
    rows = read_jsonl(source)
    obligations = []
    for row in rows:
        obligations.append({
            "case_id": row.get("case_id"), "public_obligation": None,
            "public_candidate_available": False,
            "historical_machine_status": row.get("independent_status"), "historical_reason": row.get("reason"),
            "truth_key_read": False, "source_row_sha256": __import__("hashlib").sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        })
    write_jsonl(out, obligations)
    result = {"row_count": len(obligations), "candidate_available": sum(x["public_candidate_available"] for x in obligations), "source_sha256": sha256_file(source), "truth_key_read": False, "retrospective": True}
    write_json(out.with_name("Q92_EXTRACTION_MANIFEST.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(extract(args.source, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
