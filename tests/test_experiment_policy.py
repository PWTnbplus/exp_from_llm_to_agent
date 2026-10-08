import json

import pytest

from scientific_discovery.experiment.policy import PolicyController, PolicyProvider, PolicyViolation, get_group_policy
from scientific_discovery.models.provider import LLMProvider, MockLLMProvider, OpenAICompatibleProvider, ProviderResponse, Usage
from scientific_discovery.observability.trace import TraceRecorder, read_trace


def test_group_permissions_are_hard_gates_not_prompt_conventions():
    provider = MockLLMProvider([{"final_answer": {}}])
    controller = PolicyController(get_group_policy("G1"))
    guarded = PolicyProvider(provider, controller)
    with pytest.raises(PolicyViolation, match="tools are forbidden"):
        guarded.complete([], tools=[{"type": "function", "function": {"name": "calculate_expression"}}])
    assert provider.calls == []
    assert controller.snapshot()["violations"]


def test_model_call_and_compute_budgets_are_enforced():
    controller = PolicyController(get_group_policy("G2"))
    for _ in range(2):
        controller.before_model_call([{"function": {"name": "calculate_expression"}}])
    with pytest.raises(PolicyViolation, match="model call budget"):
        controller.before_model_call([{"function": {"name": "calculate_expression"}}])
    for _ in range(4):
        controller.before_tool_call("calculate_expression", compute=True)
    with pytest.raises(PolicyViolation, match="computation budget"):
        controller.before_tool_call("calculate_expression", compute=True)


def test_retrieval_and_memory_permissions_are_recorded(tmp_path):
    path = tmp_path / "trace.jsonl"
    with TraceRecorder(path, run_id="policy-run", task_id="t", system_type="G1") as trace:
        controller = PolicyController(get_group_policy("G1"), trace=trace)
        with pytest.raises(PolicyViolation, match="retrieval"):
            controller.retrieval("web")
        with pytest.raises(PolicyViolation, match="memory"):
            controller.store_memory()
    events = read_trace(path)
    assert sum(event["event_type"] == "POLICY_CHECK" for event in events) == 2
    assert all(event["metadata"]["group"] == "G1" for event in events if event["event_type"] == "POLICY_CHECK")
    assert any(event["metadata"].get("error_type") == "policy_violation" for event in events if event["event_type"] == "ERROR")


class RetryReportingProvider(LLMProvider):
    model_name = "retry-reporting"

    def complete(self, messages, *, tools=None):
        return ProviderResponse(content=json.dumps({"final_answer": {}}), usage=Usage(), metadata={"attempt": 2})


def test_forbidden_provider_retry_is_rejected_by_group_policy():
    controller = PolicyController(get_group_policy("G1"))
    with pytest.raises(PolicyViolation, match="transport retries"):
        PolicyProvider(RetryReportingProvider(), controller).complete([], tools=None)


def test_provider_retry_configuration_is_rejected_before_any_request():
    provider = OpenAICompatibleProvider(**{"api" + "_key": "test-key"}, model_name="m", max_retries=1, input_cost_per_1k=1, output_cost_per_1k=1)
    with pytest.raises(PolicyViolation, match="provider is configured"):
        PolicyProvider(provider, PolicyController(get_group_policy("G1")))
