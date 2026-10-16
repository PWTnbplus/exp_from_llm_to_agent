"""Preregistered paired-family cluster analysis for the verified G6 subset."""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _index_unique(rows: list[dict[str, Any]], key, label: str) -> dict[Any, dict[str, Any]]:
    indexed: dict[Any, dict[str, Any]] = {}
    for row in rows:
        value = key(row)
        if value in indexed:
            raise SystemExit(f"duplicate {label}: {value!r}")
        indexed[value] = row
    return indexed


def validate_statistical_inputs(
    plan: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
    response_rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Reject input collisions before any statistical row can be overwritten."""

    plan_by_run = _index_unique(plan, lambda row: row["run_id"], "plan run_id")
    seen_arm_keys: set[tuple[Any, ...]] = set()
    for row in plan:
        arm_key = (
            row["theory_family_id"], row["cf_type"], int(row["replicate"]), row["group_id"]
        )
        if arm_key in seen_arm_keys:
            raise SystemExit(f"duplicate plan family/CF/replicate/arm: {arm_key!r}")
        seen_arm_keys.add(arm_key)

    private = _index_unique(private_rows, lambda row: row["case_id"], "private case_id")
    responses = _index_unique(response_rows, lambda row: row["run_id"], "response run_id")
    missing_response_ids = sorted(set(plan_by_run) - set(responses))
    if missing_response_ids:
        raise SystemExit(f"missing matched response run_id: {missing_response_ids!r}")
    extra_response_ids = sorted(set(responses) - set(plan_by_run))
    if extra_response_ids:
        raise SystemExit(f"unexpected response run_id: {extra_response_ids!r}")
    missing_cases = sorted({row["case_id"] for row in plan} - set(private))
    if missing_cases:
        raise SystemExit(f"missing matched private case_id: {missing_cases!r}")
    return private, responses


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    if not values:
        return float("nan")
    index = (len(values) - 1) * q
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return values[low]
    return values[low] + (values[high] - values[low]) * (index - low)


def exact_two_sided_binomial(k: int, n: int) -> float | None:
    if n == 0:
        return None
    probs = [math.comb(n, i) / (2 ** n) for i in range(n + 1)]
    observed = probs[k]
    return min(1.0, sum(prob for prob in probs if prob <= observed + 1e-15))


def summarize_pairs(pairs: list[tuple[bool, bool]], family_values: dict[str, tuple[float, float]], seed: int) -> dict[str, Any]:
    a_correct = sum(a for a, _ in pairs)
    b_correct = sum(b for _, b in pairs)
    discordant_a_only = sum(a and not b for a, b in pairs)
    discordant_b_only = sum((not a) and b for a, b in pairs)
    family_diffs = [b - a for a, b in family_values.values()]
    rng = random.Random(seed)
    bootstrap: list[float] = []
    names = list(family_values)
    for _ in range(20000):
        sampled = [family_diffs[rng.randrange(len(family_diffs))] for _ in family_diffs]
        bootstrap.append(sum(sampled) / len(sampled))
    mean_diff = sum(family_diffs) / len(family_diffs)
    return {
        "matched_runs": len(pairs),
        "matched_families": len(family_values),
        "G3_correct": a_correct,
        "G4_correct": b_correct,
        "G3_accuracy": a_correct / len(pairs) if pairs else None,
        "G4_accuracy": b_correct / len(pairs) if pairs else None,
        "family_mean_accuracy_difference_G4_minus_G3": mean_diff,
        "family_cluster_bootstrap_95_ci": [percentile(bootstrap, 0.025), percentile(bootstrap, 0.975)],
        "mcnemar_discordant_G3_only": discordant_a_only,
        "mcnemar_discordant_G4_only": discordant_b_only,
        "mcnemar_exact_two_sided_p": exact_two_sided_binomial(discordant_b_only, discordant_a_only + discordant_b_only),
        "bootstrap_seed": seed,
        "inference_note": "Family is the cluster; Wilson run-level intervals are not used for the primary arm comparison. Bootstrap and McNemar results require independent review before confirmatory claims.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plan = read_jsonl(args.plan)
    private, responses = validate_statistical_inputs(
        plan, read_jsonl(args.private), read_jsonl(args.responses)
    )
    matched: dict[tuple[str, str, int], dict[str, bool]] = defaultdict(dict)
    for row in plan:
        response = responses.get(row["run_id"])
        oracle = private.get(row["case_id"])
        if response is None or oracle is None:
            raise SystemExit(f"missing matched record: {row['run_id']}")
        key = (row["theory_family_id"], row["cf_type"], int(row["replicate"]))
        matched[key][row["group_id"]] = response.get("decision") == oracle.get("expected_decision")
    if any(set(value) != {"G3", "G4"} for value in matched.values()):
        raise SystemExit("unmatched G3/G4 pair")
    by_cf: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    by_cf_family: dict[str, dict[str, list[tuple[bool, bool]]]] = defaultdict(lambda: defaultdict(list))
    for (family, cf_type, _replicate), value in matched.items():
        pair = (value["G3"], value["G4"])
        by_cf[cf_type].append(pair)
        by_cf_family[cf_type][family].append(pair)
    reports: dict[str, Any] = {}
    seed = 20261014
    for cf_type, pairs in sorted(by_cf.items()):
        family_values = {
            family: (sum(a for a, _ in values) / len(values), sum(b for _, b in values) / len(values))
            for family, values in by_cf_family[cf_type].items()
        }
        reports[cf_type] = summarize_pairs(pairs, family_values, seed)
        seed += 1
    all_family_values: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    all_pairs: list[tuple[bool, bool]] = []
    for (family, _cf_type, _replicate), value in matched.items():
        pair = (value["G3"], value["G4"])
        all_pairs.append(pair)
        all_family_values[family].append(pair)
    reports["ALL_CF"] = summarize_pairs(
        all_pairs,
        {family: (sum(a for a, _ in values) / len(values), sum(b for _, b in values) / len(values)) for family, values in all_family_values.items()},
        seed,
    )
    output = {
        "analysis": "g6_verified23_paired_family_cluster_v1",
        "plan_rows": len(plan),
        "families": len(all_family_values),
        "primary_unit": "theory_family_id",
        "pairing": "same family, cf_type, and replicate matched across G3/G4",
        "reports": reports,
        "scientific_status": "ANALYZED_PENDING_INDEPENDENT_STATISTICAL_REVIEW",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"analysis": output["analysis"], "families": output["families"], "reports": reports}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
