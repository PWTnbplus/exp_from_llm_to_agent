from pathlib import Path

import pytest

from scientific_discovery.benchmark.base import TaskSpec
from scientific_discovery.benchmark.newtonbench_adapter import NewtonBenchOracle
from scientific_discovery.benchmark.newtonbench_adapter import ActionValidationError
from scientific_discovery.environment.budget import BudgetLedger, BudgetLimits


def test_public_description_excludes_hidden_source_tokens():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    oracle = NewtonBenchOracle(task, root, BudgetLedger(BudgetLimits()))
    text = oracle.get_public_task_description()
    assert "HIDDEN_CONSTANT" not in text
    assert "ground_truth_law" not in text
    assert "6.674e-5" not in text


def test_public_action_schema_and_oracle_enforce_apparatus_domain():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m4_snell_law:easy:v0:vanilla_equation", "NewtonBench", "m4_snell_law", "snell_law", "easy", "vanilla_equation", "v0")
    oracle = NewtonBenchOracle(task, root, BudgetLedger(BudgetLimits()))
    schema = oracle.get_action_schema()
    assert schema["properties"]["n1"]["minimum"] == 1.0
    assert schema["properties"]["angle1"]["maximum"] == 90.0
    with pytest.raises(ActionValidationError):
        oracle.run_experiment({"n1": 0.5, "n2": 1.2, "angle1": 30.0})
    with pytest.raises(ActionValidationError):
        oracle.run_experiment({"n1": 1.2, "n2": 1.2, "angle1": 91.0})
