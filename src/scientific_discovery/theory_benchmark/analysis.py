"""Grouped statistics and figures for theory benchmark result files."""
from __future__ import annotations

import json
import random
from pathlib import Path
from statistics import mean
from typing import Any

from .schema import load_benchmark


def _ci(values: list[float], seed: int = 42, n: int = 2000) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    samples = [mean(rng.choice(values) for _ in values) for _ in range(n)]
    samples.sort()
    return [samples[int(.025*n)], samples[int(.975*n)-1]]


def _rows(input_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(Path(input_dir).glob("*.json")):
        if path.name == "summary.json":
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(obj, dict) and "task_id" in obj and "validation" in obj:
                rows.append(obj)
        except (OSError, json.JSONDecodeError):
            continue
    return rows


def analyze(input_dir: Path, output_dir: Path, *, seed: int = 42) -> dict[str, Any]:
    public, _, manifest = load_benchmark()
    by_id = {row["task_id"]: row for row in public}
    rows = _rows(input_dir)
    for row in rows:
        row["task"] = by_id.get(row["task_id"], {})
    def metric(subset: list[dict[str, Any]]) -> dict[str, Any]:
        correct = [bool(row.get("validation", {}).get("answer_correct")) for row in subset]
        return {"n": len(subset), "correct": sum(correct), "accuracy": sum(correct)/len(correct) if correct else None,
                "model_errors": sum(row.get("validation", {}).get("status") == "MODEL_ERROR" for row in subset),
                "validator_errors": sum(row.get("validation", {}).get("status") == "VALIDATOR_ERROR" for row in subset)}
    by_level = {str(level): metric([r for r in rows if r["task"].get("difficulty_level") == level]) for level in (1, 2, 3)}
    by_domain = {domain: metric([r for r in rows if r["task"].get("domain") == domain]) for domain in ("Theoretical Chemistry", "Theoretical Biology")}
    by_mode = {mode: metric([r for r in rows if r.get("runner") == mode]) for mode in ("llm_only", "llm_tools", "iterative_reflection", "agent")}
    grouped: dict[str, dict[str, int]] = {}
    failures: dict[str, int] = {}
    for row in rows:
        task_id = row["task_id"]
        mode = str(row.get("runner"))
        grouped.setdefault(task_id, {})[mode] = int(bool(row.get("validation", {}).get("answer_correct")))
        if not row.get("validation", {}).get("answer_correct"):
            status = str(row.get("validation", {}).get("status", "UNKNOWN"))
            failures[status] = failures.get(status, 0) + 1
    pairs = [values["agent"]-values["llm_only"] for values in grouped.values() if "agent" in values and "llm_only" in values]
    cost = {}
    for row in rows:
        mode = str(row.get("runner"))
        used = row.get("metadata", {}).get("budget", {}).get("used", {})
        bucket = cost.setdefault(mode, {"runs": 0, "provider_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
        bucket["runs"] += 1
        bucket["provider_calls"] += int(row.get("metadata", {}).get("provider_calls", 0))
        bucket["input_tokens"] += int(used.get("input_tokens", 0))
        bucket["output_tokens"] += int(used.get("output_tokens", 0))
        bucket["cost_usd"] += float(used.get("cost_usd", 0.0))
    summary = {"benchmark": manifest.get("version", "unknown"), "n_results": len(rows), "by_level": by_level, "by_domain": by_domain,
               "by_mode": by_mode, "failure_frequency": failures, "paired_agent_minus_llm": {"n": len(pairs), "mean": mean(pairs) if pairs else None, "bootstrap_95_ci": _ci(pairs, seed=seed)}, "cost_and_tokens": cost,
               "scientific_caveat": "结果按任务保留失败分母；没有把数值核验替换成数学证明。"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        levels = ["1", "2", "3"]
        fig, ax = plt.subplots(); ax.bar(levels, [by_level[x]["accuracy"] or 0 for x in levels]); ax.set(title="Figure 1: Accuracy by difficulty", xlabel="Level", ylabel="Accuracy"); fig.savefig(output_dir / "figure1_difficulty.png", dpi=160); plt.close(fig)
        domains = list(by_domain); fig, ax = plt.subplots(); ax.bar(domains, [by_domain[x]["accuracy"] or 0 for x in domains]); ax.set(title="Figure 2: Accuracy by domain", ylabel="Accuracy"); fig.savefig(output_dir / "figure2_domain.png", dpi=160); plt.close(fig)
        modes = [x for x in by_mode if by_mode[x]["n"]]; fig, ax = plt.subplots(); ax.scatter([cost.get(x, {}).get("cost_usd", 0) for x in modes], [by_mode[x]["accuracy"] or 0 for x in modes]); ax.set(title="Figure 3: Accuracy versus cost", xlabel="Cost (USD)", ylabel="Accuracy"); fig.savefig(output_dir / "figure3_cost.png", dpi=160); plt.close(fig)
        fig, ax = plt.subplots(); labels=list(failures) or ["none"]; ax.bar(labels, [failures[x] for x in labels]); ax.set(title="Figure 4: Failure map", ylabel="Count"); fig.savefig(output_dir / "figure4_failure_map.png", dpi=160); plt.close(fig)
        summary["figures"] = ["figure1_difficulty.png", "figure2_domain.png", "figure3_cost.png", "figure4_failure_map.png"]
        (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except ImportError:
        summary["figures"] = []
    return summary
