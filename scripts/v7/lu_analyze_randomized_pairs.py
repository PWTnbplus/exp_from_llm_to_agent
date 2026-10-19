from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, write_json


def analyze(pairs: Path, transitions: Path, out: Path) -> dict:
    p, t = read_jsonl(pairs), read_jsonl(transitions)
    result = {"analysis_unit": "independent_theory_family", "families": len(p), "planned_itt": len(p), "valid_u_real": 0, "valid_u_sham": 0, "effect_real_minus_sham": None, "ci95": None, "trace_validity_separate": True, "historical_lu_u_not_pooled": True, "source_transition_count": len(t)}
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--pairs", type=Path, required=True); parser.add_argument("--transitions", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(analyze(args.pairs, args.transitions, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
