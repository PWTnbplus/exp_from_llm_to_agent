from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, write_jsonl, write_json


def run(pairs: Path, out: Path) -> dict:
    rows = read_jsonl(pairs); transitions = []
    for row in rows:
        transitions.append({"pair_id": row.get("pair_id"), "status": "INELIGIBLE_U", "observed_before": False, "observed_after": False, "reason": row.get("reason"), "model_id": row.get("model_id")})
    write_jsonl(out, transitions)
    result = {"pair_count": len(rows), "observed_transition_count": 0, "valid_u_count": 0, "api_calls_added": 0, "reused_existing_trace": True}
    write_json(out.with_name("LU_CHECKPOINT_FORK_MANIFEST.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--pairs", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(run(args.pairs, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
