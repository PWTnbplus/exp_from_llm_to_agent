import pytest
from urllib.error import URLError

from scientific_discovery.models.provider import OpenAICompatibleProvider


def test_openai_retry_errors_are_recorded_without_secrets(monkeypatch):
    attempts = []

    def fail_request(*args, **kwargs):
        attempts.append((args, kwargs))
        raise URLError("offline test")

    monkeypatch.setattr("scientific_discovery.models.provider.urlrequest.urlopen", fail_request)
    secret = "secret-test-key"
    provider = OpenAICompatibleProvider(
        **{"api" + "_key": secret},
        model_name="test-model",
        max_retries=2,
        input_cost_per_1k=1.0,
        output_cost_per_1k=1.0,
    )
    with pytest.raises(RuntimeError):
        provider.complete([{"role": "user", "content": "hello"}])

    trace = provider.audit_trace()
    assert len(attempts) == 3
    assert len(trace) == 3
    assert [item["attempt"] for item in trace] == [1, 2, 3]
    assert all(item["error"]["type"] == "URLError" for item in trace)
    assert all("secret-test-key" not in str(item) for item in trace)


def test_openai_provider_fails_closed_without_token_pricing(monkeypatch):
    def unexpected_request(*args, **kwargs):
        raise AssertionError("an unpriced API request must not be sent")

    monkeypatch.setattr("scientific_discovery.models.provider.urlrequest.urlopen", unexpected_request)
    provider = OpenAICompatibleProvider(**{"api" + "_key": "secret-test-key"}, model_name="test-model")
    with pytest.raises(RuntimeError, match="token pricing is not configured"):
        provider.complete([{"role": "user", "content": "hello"}])


def test_openai_provider_hard_cost_cap_blocks_before_request(monkeypatch):
    def unexpected_request(*args, **kwargs):
        raise AssertionError("request must be blocked by the cap")

    monkeypatch.setattr("scientific_discovery.models.provider.urlrequest.urlopen", unexpected_request)
    provider = OpenAICompatibleProvider(
        **{"api" + "_key": "secret-test-key"},
        model_name="test-model",
        input_cost_per_1k=1.0,
        output_cost_per_1k=1.0,
        max_cost_usd=0.0001,
        max_output_tokens=2048,
    )
    with pytest.raises(RuntimeError, match="hard cost cap"):
        provider.complete([{"role": "user", "content": "hello"}])
