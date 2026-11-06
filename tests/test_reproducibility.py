from pathlib import Path

from scientific_discovery.benchmark.base import TaskSpec
from scientific_discovery.benchmark.newtonbench_adapter import NewtonBenchOracle
from scientific_discovery.environment.budget import BudgetLedger, BudgetLimits


def test_newtonbench_direct_measurement_repeats_exactly():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    action = {"mass1": 2.0, "mass2": 3.0, "distance": 4.0}
    a = NewtonBenchOracle(task, root, BudgetLedger(BudgetLimits()))
    b = NewtonBenchOracle(task, root, BudgetLedger(BudgetLimits()))
    assert a.run_experiment(action).result == b.run_experiment(action).result
