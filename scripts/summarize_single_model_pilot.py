"""Compute the preregistered, non-confirmatory pilot summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scientific_discovery.evaluation.statistics import clustered_paired_bootstrap_ci, law_family_key


def summarize(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    pairs: dict[tuple[int, str], dict[str, bool]] = {}
    for row in rows:
        key = (int(row["replicate_index"]), str(row["task_id"]))
        pairs.setdefault(key, {})[str(row["runner"])] = bool(row.get("validated_success", False))
    complete_pairs = [pair for pair in pairs.values() if set(pair) == {"agent", "llm_only"}]
    deltas = [int(pair["agent"]) - int(pair["llm_only"]) for pair in complete_pairs]
    clustered = [
        (law_family_key(task_id), int(pair["agent"]) - int(pair["llm_only"]))
        for (replicate, task_id), pair in pairs.items()
        if set(pair) == {"agent", "llm_only"}
    ]
    ci = clustered_paired_bootstrap_ci(clustered, seed=20261008, repeats=10_000) if clustered else (float("nan"), float("nan"))
    arm_summary: dict[str, Any] = {}
    for runner in ("llm_only", "agent"):
        arm_rows = [row for row in rows if row.get("runner") == runner]
        arm_summary[runner] = {
            "n_registered": len(arm_rows),
            "n_completed": sum(row.get("status") == "completed" for row in arm_rows),
            "n_failed": sum(row.get("status") != "completed" for row in arm_rows),
            "validated_success_count": sum(bool(row.get("validated_success")) for row in arm_rows),
            "validated_success_rate_all_registered": sum(bool(row.get("validated_success")) for row in arm_rows) / len(arm_rows) if arm_rows else float("nan"),
        }
    return {
        "summary": "single_model_pilot_nonconfirmatory_v1",
        "model_id": payload.get("model_id"),
        "design": payload.get("design"),
        "manifest_sha256": payload.get("manifest_sha256"),
        "registered_runs": len(rows),
        "expected_runs": payload.get("expected_runs"),
        "all_pairs_present": len(complete_pairs) == 60,
        "arm_summary": arm_summary,
        "primary_endpoint": "validated_success",
        "paired_effect": "agent_minus_llm_only",
        "paired_n": len(deltas),
        "paired_agent_success_count": sum(delta == 1 for delta in deltas),
        "paired_llm_only_success_count": sum(delta == -1 for delta in deltas),
        "paired_tied_success_count": sum(delta == 0 for delta in deltas),
        "paired_mean_delta": sum(deltas) / len(deltas) if deltas else float("nan"),
        "law_family_cluster_bootstrap_95_ci": list(ci),
        "law_family_cluster_key": "NewtonBench module name",
        "bootstrap_seed": 20261008,
        "bootstrap_repeats": 10_000,
        "denominator_includes_all_registered_runs": True,
        "formal_inference_allowed": False,
        "scientific_release_allowed": False,
        "note": "This pilot summary is descriptive only. It does not establish model superiority, provider billing, immutable model identity, G0 provenance, G6 statistical validity, or G7 completion.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.input)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
