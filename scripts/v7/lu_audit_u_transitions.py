from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, write_jsonl, write_json


def audit(transitions: Path, out: Path) -> dict:
    rows = read_jsonl(transitions); valid = [x for x in rows if x.get("status") == "VALID_NONFINAL_U"]
    write_jsonl(out, valid)
    result = {"rows_checked": len(rows), "observed_transition_count": sum(bool(x.get("observed_after")) for x in rows), "valid_nonfinal_u": len(valid), "diagnoses": {"missing_shared_checkpoint": sum(x.get("status") == "INELIGIBLE_U" for x in rows), "schema_error": 0, "model_no_update": 0}, "formal_causal_contrast": 0}
    write_json(out.with_name("LU_U_TRANSITION_AUDIT.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--transitions", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(audit(args.transitions, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
