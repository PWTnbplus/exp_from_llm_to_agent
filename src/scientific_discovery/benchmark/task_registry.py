"""Task discovery and deterministic manifest construction."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import Iterable

from .base import TaskSpec


MODULE_DOMAIN = {
    "m0_gravity": "gravitation",
    "m1_coulomb_force": "coulomb_force",
    "m2_magnetic_force": "magnetic_force",
    "m3_fourier_law": "fourier_law",
    "m4_snell_law": "snell_law",
    "m5_radioactive_decay": "radioactive_decay",
    "m6_underdamped_harmonic": "underdamped_harmonic_motion",
    "m7_malus_law": "malus_law",
    "m8_sound_speed": "sound_speed",
    "m9_hooke_law": "hooke_law",
    "m10_be_distribution": "bose_einstein_distribution",
    "m11_heat_transfer": "heat_transfer",
}


def ensure_upstream_importable(repo_root: Path) -> None:
    repo_root = repo_root.resolve()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def discover_newtonbench_modules(repo_root: Path) -> list[str]:
    modules_root = repo_root / "modules"
    return sorted(
        p.name for p in modules_root.iterdir()
        if p.is_dir() and re.fullmatch(r"m\d+_.+", p.name)
    )


def enumerate_newtonbench_tasks(
    repo_root: Path,
    *,
    split: str = "test",
    seed: int = 42,
    supported_system: str = "vanilla_equation",
) -> list[TaskSpec]:
    """Enumerate the supported direct-measurement subset.

    NewtonBench advertises 324 combinations when all three system types are
    crossed with 12 domains, 3 law difficulties and 3 law variants.  The first
    controlled implementation intentionally registers the 108 direct-
    measurement tasks only.  The two dynamical system types remain explicit
    future extensions rather than silently pretending to support them.
    """

    ensure_upstream_importable(repo_root)
    tasks: list[TaskSpec] = []
    for module_name in discover_newtonbench_modules(repo_root):
        module = importlib.import_module(f"modules.{module_name}")
        get_versions = getattr(module, "get_available_law_versions", None)
        if get_versions is None:
            continue
        for difficulty in ("easy", "medium", "hard"):
            for variant in get_versions(difficulty):
                task_id = f"newtonbench:{module_name}:{difficulty}:{variant}:{supported_system}"
                tasks.append(TaskSpec(
                    task_id=task_id,
                    source="NewtonBench",
                    module=module_name,
                    domain=MODULE_DOMAIN.get(module_name, module_name),
                    law_complexity=difficulty,
                    system_complexity=supported_system,
                    law_variant=variant,
                    split=split,
                    seed=seed,
                    notes="Direct-measurement system; upstream dynamics systems are not yet registered.",
                ))
    return tasks


def stratified_select(tasks: Iterable[TaskSpec], limit: int, seed: int = 42) -> list[TaskSpec]:
    """Select a deterministic, domain-balanced prefix without using outcomes."""

    import random

    candidates = list(tasks)
    if limit <= 0:
        return []
    rng = random.Random(seed)
    groups: dict[str, list[TaskSpec]] = {}
    for task in candidates:
        groups.setdefault(task.domain, []).append(task)
    for group in groups.values():
        rng.shuffle(group)
    domains = sorted(groups)
    selected: list[TaskSpec] = []
    while len(selected) < min(limit, len(candidates)):
        progressed = False
        for domain in domains:
            if groups[domain] and len(selected) < limit:
                selected.append(groups[domain].pop())
                progressed = True
        if not progressed:
            break
    return selected
