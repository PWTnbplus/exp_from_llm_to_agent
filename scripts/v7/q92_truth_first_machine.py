from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json


def truth_first(obligations: Path, out: Path) -> dict[str, Any]:
    rows = read_jsonl(obligations)
    truth = [{"case_id": row.get("case_id"), "truth_status": "UNKNOWN", "method": "public_obligation_not_reconstructed", "private_labels_read": False, "source_row_sha256": row.get("source_row_sha256")} for row in rows]
    write_jsonl(out, truth)
    result = {"row_count": len(truth), "machine_truth_count": 0, "unknown_count": len(truth), "private_labels_read": False, "truth_key_read": False, "phase": "TRUTH_FIRST", "input_sha256": sha256_file(obligations)}
    write_json(out.with_name("Q92_TRUTH_FIRST_MANIFEST.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--obligations", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(truth_first(args.obligations, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
