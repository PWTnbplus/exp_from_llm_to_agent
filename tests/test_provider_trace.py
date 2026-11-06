import pytest
from urllib.error import URLError

from scientific_discovery.models.provider import OpenAICompatibleProvider


def test_openai_retry_errors_are_recorded_without_secrets(monkeypatch):
    attempts = []

    def fail_request(*args, **kwargs):
        attempts.append((args, kwargs))
        raise URLError("offline test")

    monkeypatch.setattr("scientific_discovery.models.provider.urlrequest.urlopen", fail_request)
    provider = OpenAICompatibleProvider(api_key="secret-test-key", model_name="test-model", max_retries=2)
    with pytest.raises(RuntimeError):
        provider.complete([{"role": "user", "content": "hello"}])

    trace = provider.audit_trace()
    assert len(attempts) == 3
    assert len(trace) == 3
    assert [item["attempt"] for item in trace] == [1, 2, 3]
    assert all(item["error"]["type"] == "URLError" for item in trace)
    assert all("secret-test-key" not in str(item) for item in trace)
