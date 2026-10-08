from scientific_discovery.environment.budget import BudgetLedger, BudgetLimits
from scientific_discovery.models.provider import MockLLMProvider
from scientific_discovery.runners.single_agent import SingleAgentRunner
from .conftest import FakeOracle


def _law():
    return {"hypothesis": "x", "equation": "y=x", "variables": ["x", "y"], "parameters": {}, "evidence": [], "predictions": [], "limitations": [], "code": "def discovered_law(x):\n    return x"}


def test_agent_can_change_action_after_feedback():
    def handler(messages, tools):
        text = messages[-1]["content"]
        if "budget is exhausted" in text:
            return {"final_law": _law()}
        if "0.5" not in text and "1.5" not in text:
            return {"action": {"x": 1}, "hypothesis": "first"}
        if "0.5" in text:
            return {"action": {"x": 2}, "hypothesis": "updated"}
        return {"final_law": _law()}

    provider = MockLLMProvider(handler=handler)
    oracle = FakeOracle([0.5, 1.5], BudgetLedger(BudgetLimits(max_experiments=2, max_api_calls=4)))
    result = SingleAgentRunner(provider, oracle, oracle.budget).run("fake")
    assert result.status == "completed"
    assert oracle.actions == [{"x": 1.0}, {"x": 2.0}]
    assert provider.calls[0]["tools"] is not None


def test_agent_budget_rejects_extra_experiment():
    provider = MockLLMProvider([{"action": {"x": 1}}, {"action": {"x": 2}}])
    oracle = FakeOracle([0.0], BudgetLedger(BudgetLimits(max_experiments=1, max_api_calls=4)))
    result = SingleAgentRunner(provider, oracle, oracle.budget).run("fake")
    assert result.status == "failed"
    assert oracle.budget.experiments == 1


def test_agent_rejects_unauthorized_tool_call():
    provider = MockLLMProvider([{"tool_call": "read_hidden_law", "arguments": {"x": 1}}])
    oracle = FakeOracle([0.0], BudgetLedger(BudgetLimits(max_experiments=1, max_api_calls=4)))
    result = SingleAgentRunner(provider, oracle, oracle.budget).run("fake")
    assert result.status == "failed"
    assert oracle.actions == []
