"""Paper-oriented three-panel summary figure."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def render_three_panel(rows: list[dict[str, Any]], output_dir: Path, *, mock: bool = False) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    runners = sorted({str(row.get("runner", "unknown")) for row in rows})
    success = [sum(bool(row.get("validation", {}).get("validated_success")) for row in rows if row.get("runner") == runner) / max(1, sum(row.get("runner") == runner for row in rows)) for runner in runners]
    errors = []
    costs = []
    for runner in runners:
        runner_rows = [row for row in rows if row.get("runner") == runner]
        errors.append(sum(float(row.get("validation", {}).get("ood_relative_rmse", 0.0) or 0.0) for row in runner_rows) / max(1, len(runner_rows)))
        costs.append(sum(float(row.get("result", {}).get("metadata", {}).get("budget", {}).get("used", {}).get("cost_usd", 0.0) or 0.0) for row in runner_rows) / max(1, len(runner_rows)))

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), constrained_layout=True)
    label = " (MOCK DATA — NOT FORMAL RESULTS)" if mock else ""
    axes[0].bar(runners, success, color=["#4169e1", "#d95f02"][:len(runners)])
    axes[0].set_title("1a. Validated discovery rate")
    axes[0].set_ylabel("VLDR")
    axes[0].set_ylim(0, 1.05)
    axes[1].bar(runners, errors, color="#4daf4a")
    axes[1].set_title("1b. OOD relative RMSE")
    axes[1].set_ylabel("Relative RMSE")
    axes[2].bar(runners, costs, color="#984ea3")
    axes[2].set_title("1c. Recorded API cost")
    axes[2].set_ylabel("USD")
    fig.suptitle("Scientific law discovery comparison" + label, fontsize=12)
    names = []
    for suffix in ("png", "pdf", "svg"):
        path = output_dir / f"figure_1_three_panel.{suffix}"
        fig.savefig(path, dpi=220 if suffix == "png" else None)
        names.append(str(path))
    plt.close(fig)
    return names
