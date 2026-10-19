"""Separate-process, read-only numerical replay for V9 certificates."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from .claim_ir import ClaimIR


def _value(expression: str, x: float) -> float:
    # This is deliberately a small evaluator separate from SymPy.  Expressions
    # are generated before the provider call and are limited by ClaimIR.
    return float(eval(expression, {"__builtins__": {}}, {"x": x}))


def replay(ir: ClaimIR) -> dict[str, Any]:
    grid = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    if ir.domain in {"x>=0", "x>0"}:
        grid = [x for x in grid if x >= 0 and (ir.domain != "x>0" or x > 0)]
    if ir.domain in {"x<=0", "x<0"}:
        grid = [x for x in grid if x <= 0 and (ir.domain != "x<0" or x < 0)]
    violations = []
    for left, right in zip(grid, grid[1:]):
        delta = _value(ir.expression, right) - _value(ir.expression, left)
        bad = delta <= 1e-12 if ir.relation in {"increasing", "nondecreasing"} else delta >= -1e-12
        if ir.relation in {"increasing", "decreasing"}:
            bad = delta <= 1e-12 if ir.relation == "increasing" else delta >= -1e-12
        if bad:
            violations.append({"x1": left, "x2": right, "delta": delta})
    status = "PROVEN_FALSE" if violations else "GRID_SUPPORTS_TRUE"
    return {"status": status, "grid_points": grid, "violations": violations, "implementation": "stdlib_numeric_replay_v1"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    out = []
    for row in rows:
        ir = ClaimIR(**row["claim_ir"])
        replayed = replay(ir)
        frozen = row.get("status") or row.get("expected_status") or (row.get("independent_certificate") or {}).get("status") or (row.get("public_proof") or {}).get("status") or (row.get("proof") or {}).get("status")
        out.append({"case_id": row.get("case_id") or row.get("task_id"), "certificate_status": frozen, "replay": replayed, "independent_match": (frozen == "PROVEN_FALSE" and replayed["status"] == "PROVEN_FALSE") or (frozen == "PROVEN_TRUE" and replayed["status"] == "GRID_SUPPORTS_TRUE")})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in out) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(out), "independent_matches": sum(x["independent_match"] for x in out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
