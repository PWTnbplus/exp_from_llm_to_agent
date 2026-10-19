from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_json


def reanalyse(frozen: Path, recovery: Path, incidents: Path, out: Path) -> dict[str, Any]:
    f, r, i = read_jsonl(frozen), read_jsonl(recovery), read_jsonl(incidents)
    result = {
        "analysis_type": "AUTOMATED_RETROSPECTIVE_REANALYSIS",
        "frozen_initial_attempt": {"n": len(f), "status_counts": dict(Counter(x.get("original_status") for x in f))},
        "protocol_eligible_retry_view": {"n": 0, "status": "RETROSPECTIVE_NOT_CONFIRMATORY"},
        "new_append_recovery_view": {"n": len(r), "status_counts": dict(Counter(x.get("state_status") for x in r)), "not_independent_n": True},
        "prospective_new_run": {"n": 0, "status": "NO_NEW_G7_CALLS_REQUIRED_REUSED_TRACE_BACKED_DATA"},
        "historical_genuine_lifecycle_failures": sum(x.get("classification") == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY" for x in i),
        "formal_denominators": {"frozen": 1288, "recovery": 150}, "pooled": False,
        "source_hashes": {"frozen": sha256_file(frozen), "recovery": sha256_file(recovery), "incidents": sha256_file(incidents)},
        "scientific_release_allowed": False,
    }
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--frozen", type=Path, required=True); parser.add_argument("--recovery", type=Path, required=True); parser.add_argument("--incidents", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(reanalyse(args.frozen, args.recovery, args.incidents, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
