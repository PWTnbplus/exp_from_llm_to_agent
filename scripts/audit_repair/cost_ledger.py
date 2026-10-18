"""Atomic paid-call reservation ledger.

The ledger is deliberately provider-agnostic.  It records reservations and
settlements, and refuses a request before it leaves the process when any
declared global, G7, or worker ceiling would be exceeded.  Historical costs
are entered explicitly by an auditor; they are never inferred from a missing
receipt.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    scope: str
    worker: str
    amount: float


class CostLedger:
    def __init__(self, path: Path, *, global_cap: float = 200.0,
                 g7_cap: float = 60.0, worker_cap: float = 5.0) -> None:
        self.path = Path(path)
        self.global_cap = float(global_cap)
        self.g7_cap = float(g7_cap)
        self.worker_cap = float(worker_cap)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL, worker TEXT NOT NULL, kind TEXT NOT NULL,
                    amount REAL NOT NULL, ref TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS reservations (
                    reservation_id TEXT PRIMARY KEY, scope TEXT NOT NULL,
                    worker TEXT NOT NULL, reserved REAL NOT NULL,
                    settled REAL, status TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def _totals(self, db: sqlite3.Connection, scope: str, worker: str) -> tuple[float, float, float, float]:
        historical = db.execute(
            # ``scope=all`` is the global historical total.  A scoped entry
            # such as G7 is a sub-budget annotation and must not be added a
            # second time to the global ceiling.
            "SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope='all' AND kind IN ('historical','historical_confirmed','historical_unbilled_ceiling')"
        ).fetchone()[0]
        settled = db.execute(
            "SELECT COALESCE(SUM(settled),0) FROM reservations WHERE status='settled'"
        ).fetchone()[0]
        inflight = db.execute(
            "SELECT COALESCE(SUM(reserved),0) FROM reservations WHERE status='reserved'"
        ).fetchone()[0]
        scoped_historical = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope=? AND kind IN ('historical','historical_confirmed','historical_unbilled_ceiling')",
            (scope,),
        ).fetchone()[0]
        worker_historical = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope=? AND worker=? AND kind IN ('historical','historical_confirmed','historical_unbilled_ceiling')",
            (scope, worker),
        ).fetchone()[0]
        scoped_settled = db.execute(
            "SELECT COALESCE(SUM(settled),0) FROM reservations WHERE scope=? AND status='settled'", (scope,)
        ).fetchone()[0]
        worker_settled = db.execute(
            "SELECT COALESCE(SUM(settled),0) FROM reservations WHERE scope=? AND worker=? AND status='settled'",
            (scope, worker),
        ).fetchone()[0]
        scoped_inflight = db.execute(
            "SELECT COALESCE(SUM(reserved),0) FROM reservations WHERE scope=? AND status='reserved'", (scope,)
        ).fetchone()[0]
        worker_inflight = db.execute(
            "SELECT COALESCE(SUM(reserved),0) FROM reservations WHERE scope=? AND worker=? AND status='reserved'",
            (scope, worker),
        ).fetchone()[0]
        return (float(historical + settled), float(inflight),
                float(scoped_historical + scoped_settled + scoped_inflight),
                float(worker_historical + worker_settled + worker_inflight))

    def add_historical(self, amount: float, *, ref: str, scope: str = "all", worker: str = "all",
                       evidence_class: str = "confirmed") -> None:
        if amount < 0:
            raise ValueError("historical amount must be non-negative")
        if evidence_class not in {"confirmed", "unbilled_ceiling"}:
            raise ValueError("evidence_class must be confirmed or unbilled_ceiling")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT OR IGNORE INTO entries(scope,worker,kind,amount,ref) VALUES(?,?,?,?,?)",
                (scope, worker, f"historical_{evidence_class}", float(amount), ref),
            )
            db.execute("COMMIT")

    def reserve(self, amount: float, *, scope: str, worker: str, ref: str | None = None) -> Reservation:
        if amount <= 0:
            raise ValueError("reservation amount must be positive")
        reservation_id = ref or str(uuid.uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if scope == "g7":
                unknown_worker_history = db.execute(
                    "SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope='g7' AND worker='all' AND kind IN ('historical','historical_confirmed','historical_unbilled_ceiling')"
                ).fetchone()[0]
                if float(unknown_worker_history) > 0:
                    db.execute("ROLLBACK")
                    raise RuntimeError("G7 historical worker allocation is unavailable; per-worker cap is fail-closed")
            total, inflight, scoped, worker_total = self._totals(db, scope, worker)
            if total + inflight + amount > self.global_cap + 1e-12:
                db.execute("ROLLBACK")
                raise RuntimeError("global cost ledger reservation would exceed cap")
            if scope == "g7" and scoped + amount > self.g7_cap + 1e-12:
                db.execute("ROLLBACK")
                raise RuntimeError("G7 cost ledger reservation would exceed aggregate cap")
            if scope == "g7" and worker_total + amount > self.worker_cap + 1e-12:
                db.execute("ROLLBACK")
                raise RuntimeError("G7 worker cost ledger reservation would exceed cap")
            db.execute(
                "INSERT INTO reservations(reservation_id,scope,worker,reserved,settled,status) VALUES(?,?,?,?,?,?)",
                (reservation_id, scope, worker, float(amount), None, "reserved"),
            )
            db.execute("COMMIT")
        return Reservation(reservation_id, scope, worker, float(amount))

    def settle(self, reservation_id: str, actual: float) -> None:
        if actual < 0:
            raise ValueError("settled amount must be non-negative")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT reserved,status FROM reservations WHERE reservation_id=?", (reservation_id,)
            ).fetchone()
            if row is None:
                db.execute("ROLLBACK")
                raise KeyError(reservation_id)
            if row[1] != "reserved":
                db.execute("ROLLBACK")
                raise RuntimeError(f"reservation already settled: {reservation_id}")
            if actual > float(row[0]) + 1e-12:
                db.execute("ROLLBACK")
                raise RuntimeError("provider usage exceeded reserved worst-case amount")
            db.execute(
                "UPDATE reservations SET settled=?,status='settled' WHERE reservation_id=?",
                (float(actual), reservation_id),
            )
            db.execute("COMMIT")

    def snapshot(self) -> dict[str, object]:
        with self._connect() as db:
            historical = float(db.execute("SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope='all' AND kind IN ('historical','historical_confirmed','historical_unbilled_ceiling')").fetchone()[0])
            confirmed = float(db.execute("SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope='all' AND kind IN ('historical','historical_confirmed')").fetchone()[0])
            unbilled = float(db.execute("SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope='all' AND kind='historical_unbilled_ceiling'").fetchone()[0])
            g7_history = float(db.execute("SELECT COALESCE(SUM(amount),0) FROM entries WHERE scope='g7' AND kind IN ('historical','historical_confirmed','historical_unbilled_ceiling')").fetchone()[0])
            settled = float(db.execute("SELECT COALESCE(SUM(settled),0) FROM reservations WHERE status='settled'").fetchone()[0])
            inflight = float(db.execute("SELECT COALESCE(SUM(reserved),0) FROM reservations WHERE status='reserved'").fetchone()[0])
            return {
                "global_cap_usd": self.global_cap,
                "g7_cap_usd": self.g7_cap,
                "worker_cap_usd": self.worker_cap,
                "historical_entered_usd": historical,
                "historical_confirmed_usd": confirmed,
                "historical_unbilled_conservative_ceiling_usd": unbilled,
                "historical_g7_subcap_usd": g7_history,
                "settled_new_usd": settled,
                "inflight_reserved_usd": inflight,
                "safe_remaining_if_all_reservations_settle_usd": self.global_cap - historical - settled - inflight,
            }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--global-cap", type=float, default=200.0)
    parser.add_argument("--g7-cap", type=float, default=60.0)
    parser.add_argument("--worker-cap", type=float, default=5.0)
    parser.add_argument("--add-historical", type=float)
    parser.add_argument("--ref")
    args = parser.parse_args()
    ledger = CostLedger(args.db, global_cap=args.global_cap, g7_cap=args.g7_cap, worker_cap=args.worker_cap)
    if args.add_historical is not None:
        if not args.ref:
            parser.error("--ref is required with --add-historical")
        ledger.add_historical(args.add_historical, ref=args.ref)
    print(json.dumps(ledger.snapshot(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
