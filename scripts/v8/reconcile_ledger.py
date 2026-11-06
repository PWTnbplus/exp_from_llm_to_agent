"""Reconcile one orphaned reservation left by an interrupted V8 process."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--reservation", required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    with sqlite3.connect(args.db) as db:
        row = db.execute("SELECT reserved,settled,status FROM reservations WHERE reservation_id=?", (args.reservation,)).fetchone()
        if row is None:
            raise SystemExit("reservation not found")
        db.execute("UPDATE reservations SET settled=0.0,status='settled' WHERE reservation_id=?", (args.reservation,))
    record = {"reservation_id": args.reservation, "previous": {"reserved": row[0], "settled": row[1], "status": row[2]}, "reconciled_settled": 0.0, "reason": "orphaned reservation created by interrupted process; no matching provider trace or model response"}
    args.audit.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()

