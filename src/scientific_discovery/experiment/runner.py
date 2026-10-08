"""One-task orchestration for discovery followed by blind validation."""

from __future__ import annotations

from pathlib import Path

from ..benchmark.base import TaskSpec
from ..benchmark.newtonbench_adapter import NewtonBenchOracle
from ..environment.budget import BudgetLedger, BudgetLimits
from ..evaluation.validation import ValidationEnvironment
from ..models.provider import LLMProvider
from ..runners.llm_only import LLMOnlyRunner
from ..runners.single_agent import SingleAgentRunner
from .recorder import ResultRecorder


def run_one(
    task: TaskSpec,
    repo_root: Path,
    provider: LLMProvider,
    runner_name: str,
    limits: BudgetLimits,
    output_dir: Path | None = None,
) -> tuple[object, dict]:
    budget = BudgetLedger(limits)
    oracle = NewtonBenchOracle(task, repo_root, budget)
    runner = LLMOnlyRunner(provider, oracle, budget) if runner_name == "llm_only" else SingleAgentRunner(provider, oracle, budget)
    result = runner.run(task.task_id)
    validation = ValidationEnvironment(repo_root).validate(task, result.law)
    if output_dir is not None:
        ResultRecorder(output_dir).write(result, validation)
    return result, validation
