import pytest

from scientific_discovery.environment.budget import BudgetExceeded, BudgetLedger, BudgetLimits


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
