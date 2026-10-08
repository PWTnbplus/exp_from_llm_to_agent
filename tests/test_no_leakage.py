from pathlib import Path

from scientific_discovery.benchmark.base import TaskSpec
from scientific_discovery.benchmark.newtonbench_adapter import NewtonBenchOracle
from scientific_discovery.environment.budget import BudgetLedger, BudgetLimits


def test_public_description_excludes_hidden_source_tokens():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    oracle = NewtonBenchOracle(task, root, BudgetLedger(BudgetLimits()))
    text = oracle.get_public_task_description()
    assert "HIDDEN_CONSTANT" not in text
    assert "ground_truth_law" not in text
    assert "6.674e-5" not in text
