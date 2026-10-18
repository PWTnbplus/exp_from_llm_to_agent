from __future__ import annotations

import threading
from pathlib import Path

import pytest

from scripts.audit_repair.cost_ledger import CostLedger


def test_cost_ledger_reservation_settlement_and_cap(tmp_path: Path) -> None:
    ledger = CostLedger(tmp_path / "cost.sqlite", global_cap=10, g7_cap=6, worker_cap=3)
    reservation = ledger.reserve(2, scope="g7", worker="2", ref="r1")
    ledger.settle(reservation.reservation_id, 1.5)
    assert ledger.snapshot()["settled_new_usd"] == 1.5
    with pytest.raises(RuntimeError, match="worker"):
        ledger.reserve(2, scope="g7", worker="2", ref="r2")


def test_cost_ledger_atomic_concurrent_reservations(tmp_path: Path) -> None:
    ledger_path = tmp_path / "cost.sqlite"
    errors: list[Exception] = []

    def reserve(index: int) -> None:
        try:
            CostLedger(ledger_path, global_cap=1, g7_cap=1, worker_cap=1).reserve(
                0.6, scope="g7", worker=str(index), ref=f"r{index}"
            )
        except Exception as exc:  # exactly one reservation may fit
            errors.append(exc)

    threads = [threading.Thread(target=reserve, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(errors) == 1


def test_historical_global_total_and_g7_subcap_are_not_double_counted(tmp_path: Path) -> None:
    ledger = CostLedger(tmp_path / "cost.sqlite", global_cap=20, g7_cap=6, worker_cap=3)
    ledger.add_historical(10, ref="global", scope="all", worker="all")
    ledger.add_historical(3, ref="g7", scope="g7", worker="all")
    snapshot = ledger.snapshot()
    assert snapshot["historical_entered_usd"] == 10.0
    assert snapshot["historical_confirmed_usd"] == 10.0
    assert snapshot["historical_g7_subcap_usd"] == 3.0
    assert snapshot["safe_remaining_if_all_reservations_settle_usd"] == 10.0


def test_g7_unknown_worker_historical_allocation_fails_closed(tmp_path: Path) -> None:
    ledger = CostLedger(tmp_path / "cost.sqlite", global_cap=20, g7_cap=6, worker_cap=3)
    ledger.add_historical(3, ref="g7", scope="g7", worker="all")
    with pytest.raises(RuntimeError, match="worker allocation"):
        ledger.reserve(0.1, scope="g7", worker="0", ref="new")
