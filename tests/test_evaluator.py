from pathlib import Path

from scientific_discovery.benchmark.base import TaskSpec
from scientific_discovery.evaluation.law_recovery import LawCandidate, NewtonBenchLawEvaluator
from scientific_discovery.utils.json_protocol import ProtocolError


def test_independent_validation_accepts_exact_mock_law():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    law = LawCandidate.from_payload({
        "hypothesis": "direct law", "equation": "F=C*m1*m2/r^1.5", "variables": ["mass1", "mass2", "distance"], "parameters": {},
        "evidence": [], "predictions": [], "limitations": [],
        "code": "def discovered_law(mass1, mass2, distance):\n    return 6.674e-5 * mass1 * mass2 / (distance ** 1.5)",
    }, task.task_id)
    result = NewtonBenchLawEvaluator(root, test_points=16).evaluate(task, law)
    assert result["validated_success"] is True
    assert result["symbolic_judge_used"] is False
    assert result["structural_recovery"] is None
    assert result["mechanistic_validity"] == "not_implemented"


def _candidate(task_id, code, equation="candidate"):
    return LawCandidate.from_payload({
        "hypothesis": "test", "equation": equation,
        "variables": ["mass1", "mass2", "distance"], "parameters": {},
        "evidence": [], "predictions": [], "limitations": [], "code": code,
    }, task_id)


def test_evaluator_rejects_wrong_parameter_and_illegal_code():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    evaluator = NewtonBenchLawEvaluator(root, test_points=16)
    wrong = _candidate(task.task_id, "def discovered_law(mass1, mass2, distance):\n    return 2.0 * mass1 * mass2 / (distance ** 1.5)")
    illegal = _candidate(task.task_id, "import os\ndef discovered_law(mass1, mass2, distance):\n    return 0.0")
    assert evaluator.evaluate(task, wrong)["validated_success"] is False
    assert evaluator.evaluate(task, illegal)["validated_success"] is False


def test_evaluator_rejects_finite_region_overfit_and_bad_format():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    evaluator = NewtonBenchLawEvaluator(root, test_points=32)
    overfit = _candidate(task.task_id, "def discovered_law(mass1, mass2, distance):\n    return (6.674e-5 * mass1 * mass2 / (distance ** 1.5)) if distance < 5 else 0.0")
    assert evaluator.evaluate(task, overfit)["validated_success"] is False
    try:
        LawCandidate.from_payload("not json", task.task_id)
    except ProtocolError:
        pass
    else:
        raise AssertionError("invalid law format was accepted")


def test_algebraically_equivalent_code_passes_numeric_but_not_mechanistic_claim():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    candidate = _candidate(task.task_id, "def discovered_law(mass1, mass2, distance):\n    return (6.674e-5 * (mass1 * mass2)) / (distance ** 1.5)", equation="F = C*(m1*m2)/r^1.5")
    result = NewtonBenchLawEvaluator(root, test_points=16).evaluate(task, candidate)
    assert result["numeric_fit"] is True
    assert result["mechanistic_validity"] == "not_implemented"
