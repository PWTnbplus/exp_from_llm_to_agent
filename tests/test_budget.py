import pytest

from scientific_discovery.environment.budget import BudgetExceeded, BudgetLedger, BudgetLimits
from scientific_discovery.runners.common import ensure_provider_call


def test_experiment_budget_is_hard_limit():
    ledger = BudgetLedger(BudgetLimits(max_experiments=1, max_measurements=1))
    ledger.consume_experiment()
    with pytest.raises(BudgetExceeded):
        ledger.consume_experiment()


def test_api_cost_budget_is_hard_limit():
    ledger = BudgetLedger(BudgetLimits(max_cost_usd=0.01))
    ledger.consume_api(1, 1, 0.01)
    with pytest.raises(BudgetExceeded):
        ledger.consume_api(1, 1, 0.001)


def test_provider_timeout_is_clamped_through_local_wrappers():
    class Provider:
        def __init__(self):
            self.timeout = 90.0

    class Wrapper:
        def __init__(self, provider):
            self.provider = provider

    provider = Provider()
    ledger = BudgetLedger(BudgetLimits(max_runtime_seconds=0.2, max_api_calls=1))
    ensure_provider_call(ledger, Wrapper(Wrapper(provider)))
    assert 0.1 <= provider.timeout <= 0.2
