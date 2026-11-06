from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, write_jsonl, write_json


def derive(dag: Path, out: Path) -> dict[str, Any]:
    rows = read_jsonl(dag)
    frozen = [x for x in rows if x.get("lineage_kind") == "FROZEN_ORIGINAL"]
    recovery = [x for x in rows if x.get("lineage_kind") == "APPEND_ONLY_RECOVERY"]
    # Selection is deliberately frozen and does not prefer a recovery result.
    canonical = frozen
    write_jsonl(out, canonical)
    result = {
        "frozen_initial_attempt": {"n": len(frozen), "success": sum(x.get("original_status") == "completed" for x in frozen)},
        "protocol_eligible_retry_view": {"n": 0, "reason": "no historical retry rule permits pooling in the frozen confirmatory view"},
        "new_append_recovery_view": {"n": len(recovery), "mapped_states": len({x.get("state_id") for x in recovery})},
        "prospective_new_run": {"n": 0, "not_created_by_retrospective_derivation": True},
        "trace_validity_vs_task_correctness_separate": True,
        "canonical_count": len(canonical), "formal_denominator_preserved": 1288,
        "status_counts": dict(Counter(str(x.get("original_status")) for x in frozen)),
    }
    write_json(out.with_name("G7_CANONICAL_DERIVATION.json"), result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--dag", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(derive(args.dag, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
