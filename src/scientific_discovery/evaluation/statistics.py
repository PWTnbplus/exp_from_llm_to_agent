"""Small deterministic paired bootstrap helper."""

from __future__ import annotations

import random
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
