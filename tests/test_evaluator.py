from pathlib import Path

from scientific_discovery.benchmark.base import TaskSpec
from scientific_discovery.evaluation.law_recovery import LawCandidate, NewtonBenchLawEvaluator
from scientific_discovery.evaluation.validation import ValidationEnvironment
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
    assert result["official_numeric_evaluator"] is False
    assert result["upstream_ground_truth_function_used"] is True
    assert result["success_definition"] == "numeric_fit_and_structural_recovery_and_ood"
    assert result["symbolic_judge_used"] is False
    assert result["structural_recovery"] is True
    assert result["ood_fit"] is True
    assert result["mechanistic_validity"] is True
    assert result["equivalence_class"] == "canonical_ast"
    assert result["scoring_protocol_version"] == "scoring-v1"


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
    wrong_result = evaluator.evaluate(task, wrong)
    assert wrong_result["structural_recovery"] is False
    assert wrong_result["ood_fit"] is False


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


def test_algebraically_equivalent_code_passes_structural_and_mechanistic_criteria():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    candidate = _candidate(task.task_id, "def discovered_law(mass1, mass2, distance):\n    return (6.674e-5 * (mass1 * mass2)) / (distance ** 1.5)", equation="F = C*(m1*m2)/r^1.5")
    result = NewtonBenchLawEvaluator(root, test_points=16).evaluate(task, candidate)
    assert result["numeric_fit"] is True
    assert result["ood_fit"] is True
    assert result["structural_recovery"] is True
    assert result["mechanistic_validity"] is True
    assert result["validated_success"] is True


def test_numeric_fit_alone_cannot_pass_with_ood_or_structural_failure():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    candidate = _candidate(
        task.task_id,
        "def discovered_law(mass1, mass2, distance):\n"
        "    exact = 6.674e-5 * mass1 * mass2 / (distance ** 1.5)\n"
        "    return exact if distance < 100 else 0.0",
    )
    result = NewtonBenchLawEvaluator(root, test_points=16).evaluate(task, candidate)
    assert result["numeric_fit"] is True
    assert result["ood_fit"] is False
    assert result["structural_recovery"] is False
    assert result["mechanistic_validity"] is False
    assert result["validated_success"] is False


def test_preregistered_scoring_config_matches_evaluator_protocol():
    import json

    from scientific_discovery.evaluation.scoring import scoring_protocol

    config = json.loads((Path(__file__).parents[1] / "configs" / "evaluation.json").read_text(encoding="utf-8"))
    protocol = scoring_protocol()
    for key, value in protocol.items():
        assert config[key] == value


def test_failed_submission_uses_explicit_scoring_failure_schema():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    result = ValidationEnvironment(root).validate(task, {"error": "provider output was malformed"})
    assert result["validated_success"] is False
    assert result["numeric_fit"] is False
    assert result["ood_fit"] is False
    assert result["structural_recovery"] is False
    assert result["mechanistic_validity"] is False
    assert result["success_definition"] == "numeric_fit_and_structural_recovery_and_ood"


def test_validation_points_respect_public_snell_domain():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m4_snell_law:easy:v0:vanilla_equation", "NewtonBench", "m4_snell_law", "snell_law", "easy", "vanilla_equation", "v0")
    actions = NewtonBenchLawEvaluator(root, test_points=32)._actions(task, split="validation")
    assert all(1.0 <= action["n1"] <= 1.5 for action in actions)
    assert all(1.0 <= action["n2"] <= 1.5 for action in actions)
    assert all(0.0 <= action["angle1"] <= 90.0 for action in actions)


def test_ood_interventions_are_deterministic_and_distribution_shifted():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m0_gravity:easy:v0:vanilla_equation", "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0")
    evaluator = NewtonBenchLawEvaluator(root, test_points=16, ood_points=16)
    first = evaluator._actions(task, split="ood")
    second = evaluator._actions(task, split="ood")
    validation = evaluator._actions(task, split="validation")
    assert first == second
    assert first != validation
    assert len(first) == 16


def test_structural_recovery_resolves_upstream_local_constants():
    root = Path(__file__).parents[1] / "third_party" / "NewtonBench"
    task = TaskSpec("newtonbench:m9_hooke_law:easy:v0:vanilla_equation", "NewtonBench", "m9_hooke_law", "hooke_law", "easy", "vanilla_equation", "v0")
    candidate = LawCandidate.from_payload({
        "hypothesis": "test", "equation": "U = 2*k*x^2", "variables": ["x"], "parameters": {},
        "evidence": [], "predictions": [], "limitations": [],
        "code": "def discovered_law(x):\n    return 2 * 231.141 * x**2",
    }, task.task_id)
    result = NewtonBenchLawEvaluator(root, test_points=16).evaluate(task, candidate)
    assert result["validated_success"] is True
    assert result["structural_recovery"] is True
    assert result["mechanistic_validity"] is True
