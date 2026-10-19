from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json
from scripts.v7.math_claim_ir import ClaimParseError, parse_claim


def _claim_from_row(row: dict[str, Any]) -> str | None:
    for key in ("claim", "candidate_claim", "public_claim", "revised_claim"):
        if isinstance(row.get(key), str):
            return row[key]
    return None


def extract(source: Path, out: Path, frozen_denominator: int = 552) -> dict[str, Any]:
    rows = read_jsonl(source)
    units: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        claim_text = _claim_from_row(row)
        ir = None
        parse_error = "missing_public_claim_text"
        if claim_text:
            try:
                ir = parse_claim(claim_text)
                parse_error = None
            except ClaimParseError as exc:
                parse_error = str(exc)
        units.append({
            "unit_index": index, "case_id": row.get("case_id"), "attempt_id": row.get("attempt_id"),
            "cf_type": row.get("cf_type"), "source_row_sha256": hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "historical_verdict": row.get("verdict"), "historical_reason": row.get("production_reason_code"),
            "claim_text_present": claim_text is not None, "claim_text": claim_text,
            "claim_ir": ir, "parse_error": parse_error,
            "truth_source": "public_claim_only" if ir else "none",
        })
    write_jsonl(out, units)
    manifest = {
        "source": str(source.resolve()), "source_sha256": sha256_file(source), "row_count": len(rows),
        "parsed_count": sum(x["claim_ir"] is not None for x in units), "frozen_formal_denominator": frozen_denominator,
        "historical_input_untouched": True,
    }
    write_json(out.with_name("G6_EXTRACT_MANIFEST.json"), manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frozen-denominator", type=int, default=552)
    args = parser.parse_args(); result = extract(args.source, args.out, args.frozen_denominator)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
