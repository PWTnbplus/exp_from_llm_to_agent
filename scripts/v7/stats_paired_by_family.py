from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, write_json


def analyse(g7: Path, lu: Path, q: Path, out: Path) -> dict:
    g7_rows = read_jsonl(g7); lu_rows = read_jsonl(lu); q_rows = read_jsonl(q)
    result = {
        "analysis_version": "v7-machine-stats-v1", "g7_frozen_n": len(g7_rows), "g7_recovery_not_pooled": True,
        "lu_independent_families": len(lu_rows), "lu_valid_u": 0, "q_machine_rows": len(q_rows),
        "cluster_bootstrap_95_ci": None, "mcnemar": None,
        "reason_no_effect_estimate": "no validated real-vs-sham U contrast and no machine truth for historical Q",
        "all_planned_denominators_retained": True,
    }
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--g7", type=Path, required=True); parser.add_argument("--lu", type=Path, required=True); parser.add_argument("--q", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(analyse(args.g7, args.lu, args.q, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
