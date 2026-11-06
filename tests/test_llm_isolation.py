from scientific_discovery.environment.budget import BudgetLedger, BudgetLimits
from scientific_discovery.models.provider import MockLLMProvider
from scientific_discovery.runners.llm_only import LLMOnlyRunner
from .conftest import FakeOracle


def _law():
    return {"hypothesis": "x", "equation": "y=x", "variables": ["x", "y"], "parameters": {}, "evidence": [], "predictions": [], "limitations": [], "code": "def discovered_law(x):\n    return x"}


def test_plan_is_frozen_and_intermediate_feedback_is_not_seen():
    responses = [{"experiments": [{"x": 1}, {"x": 2}]}, _law()]
    provider_a = MockLLMProvider(responses)
    oracle_a = FakeOracle([1.0, 2.0], BudgetLedger(BudgetLimits(max_experiments=2, max_api_calls=4)))
    result_a = LLMOnlyRunner(provider_a, oracle_a, oracle_a.budget).run("fake")

    provider_b = MockLLMProvider(responses)
    oracle_b = FakeOracle([99.0, -100.0], BudgetLedger(BudgetLimits(max_experiments=2, max_api_calls=4)))
    result_b = LLMOnlyRunner(provider_b, oracle_b, oracle_b.budget).run("fake")

    assert result_a.status == result_b.status == "completed"
    assert result_a.plan_hash == result_b.plan_hash
    assert oracle_a.actions == oracle_b.actions
    assert len(provider_a.calls) == 2
    assert all(call["tools"] is None for call in provider_a.calls)
    assert len(result_a.metadata["provider_trace"]) == 2
    assert all(call["request"]["tools"] is None for call in result_a.metadata["provider_trace"])
    assert "1.0" not in provider_a.calls[0]["messages"][1]["content"]
    assert "99.0" not in provider_b.calls[0]["messages"][1]["content"]


def test_llm_only_does_not_add_experiments_after_final_inference():
    provider = MockLLMProvider([{"experiments": [{"x": 1}]}, _law()])
    oracle = FakeOracle([1.0], BudgetLedger(BudgetLimits(max_experiments=1, max_api_calls=4)))
    result = LLMOnlyRunner(provider, oracle, oracle.budget).run("fake")
    assert result.status == "completed"
    assert oracle.budget.experiments == 1
    assert oracle.closed


def test_api_slot_is_checked_before_provider_call():
    provider = MockLLMProvider([{"experiments": []}, _law()])
    oracle = FakeOracle([1.0], BudgetLedger(BudgetLimits(max_experiments=1, max_api_calls=0)))
    result = LLMOnlyRunner(provider, oracle, oracle.budget).run("fake")
    assert result.status == "failed"
    assert provider.calls == []
