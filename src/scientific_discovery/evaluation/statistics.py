"""Small deterministic paired bootstrap helper."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Iterable


def paired_bootstrap_ci(deltas: Iterable[float], seed: int = 42, repeats: int = 2000) -> tuple[float, float]:
    values = list(float(v) for v in deltas)
    if not values:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    means = []
    for _ in range(repeats):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(0.025 * (len(means) - 1))], means[int(0.975 * (len(means) - 1))]


def law_family_key(task_id: str) -> str:
    """Return the preregistered cluster key for a benchmark task."""

    parts = str(task_id).split(":")
    if len(parts) >= 2 and parts[0] == "newtonbench" and parts[1]:
        return parts[1]
    return str(task_id)


def clustered_paired_bootstrap_ci(
    clustered_deltas: Iterable[tuple[str, float]],
    *,
    seed: int = 20261008,
    repeats: int = 10_000,
) -> tuple[float, float]:
    """Bootstrap paired deltas by law-family cluster, not by task row."""

    groups: dict[str, list[float]] = defaultdict(list)
    for cluster, delta in clustered_deltas:
        groups[str(cluster)].append(float(delta))
    if not groups:
        return float("nan"), float("nan")
    if repeats <= 0:
        raise ValueError("repeats must be positive")

    # The point estimate remains task-run based; the interval resamples family
    # means so variants and repeated seeds do not become independent families.
    cluster_means = [sum(values) / len(values) for values in groups.values()]
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(repeats):
        sample = [cluster_means[rng.randrange(len(cluster_means))] for _ in cluster_means]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(0.025 * (len(means) - 1))], means[int(0.975 * (len(means) - 1))]
