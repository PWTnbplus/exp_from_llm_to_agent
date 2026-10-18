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
