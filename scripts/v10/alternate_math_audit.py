"""Post-run alternate exact math audit.

The primary V10 certificates are immutable.  This audit uses a stronger
polynomial monotonicity theorem: a nonzero polynomial derivative with the
correct weak sign on an interval gives strict monotonicity, so isolated
boundary zeros do not become false UNKNOWN results.  It is diagnostic only
and never rewrites the frozen truth or model scores.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sympy as sp

from scripts.v9.common import read_jsonl, write_json


def _condition(domain: str, x: sp.Symbol) -> Any:
    return {"all_real": True, "x>=0": x >= 0, "x>0": x > 0, "x<=0": x <= 0, "x<0": x < 0}.get(domain, True)


def _samples(domain: str) -> list[int]:
    values = [-3, -2, -1, 0, 1, 2, 3]
    if domain in {"x>=0", "x>0"}:
        values = [v for v in values if v >= 0 and (domain != "x>0" or v > 0)]
    if domain in {"x<=0", "x<0"}:
        values = [v for v in values if v <= 0 and (domain != "x<0" or v < 0)]
    return values


def prove(expression: str, relation: str, domain: str) -> dict[str, Any]:
    x = sp.Symbol("x", real=True)
    try:
        expr = sp.sympify(expression, locals={"x": x}, evaluate=True)
        derivative = sp.factor(sp.diff(expr, x))
        condition = _condition(domain, x)
        target = derivative >= 0 if relation == "increasing" else derivative <= 0
        bad = sp.reduce_inequalities([condition, sp.Not(target)], x) if condition is not True else sp.reduce_inequalities([sp.Not(target)], x)
        if bad is sp.false and sp.simplify(derivative) != 0:
            return {"status": "PROVEN_TRUE", "method": "nonzero_polynomial_derivative_weak_sign_implies_strict_monotonicity", "derivative": str(derivative), "bad_region": str(bad)}
        for left in _samples(domain):
            for right in _samples(domain):
                if right <= left:
                    continue
                delta = sp.simplify(expr.subs(x, right) - expr.subs(x, left))
                bad_delta = delta <= 0 if relation == "increasing" else delta >= 0
                if bad_delta:
                    return {"status": "PROVEN_FALSE", "method": "exact_rational_counterexample", "derivative": str(derivative), "witness": {"x1": left, "x2": right, "delta": str(delta)}}
        return {"status": "UNKNOWN", "method": "alternate_method_exhausted", "derivative": str(derivative), "bad_region": str(bad)}
    except Exception as exc:
        return {"status": "UNKNOWN", "method": f"error={type(exc).__name__}"}


def audit(run_root: Path, audit_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for namespace, key in [("g6", "case_id"), ("q", "task_id"), ("g7", "task_id"), ("lu", "task_id")]:
        for truth in read_jsonl(run_root / "private_truth" / f"{namespace}.jsonl"):
            claim = truth["claim_ir"]
            result = prove(claim["expression"], claim["relation"], claim["domain"])
            rows.append({"namespace": namespace, "id": truth[key], "expression": claim["expression"], "relation": claim["relation"], "domain": claim["domain"], "primary_frozen_status": (truth.get("machine_certificate") or truth.get("real_certificate") or {}).get("status"), "alternate_status": result["status"], "certificate": result})
    result = {
        "audit_type": "ALTERNATE_EXACT_MATH_DIAGNOSTIC",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_frozen_truth_unchanged": True,
        "model_scores_unchanged": True,
        "rows": len(rows),
        "alternate_status_counts": dict(Counter(row["alternate_status"] for row in rows)),
        "primary_status_counts": dict(Counter(row["primary_frozen_status"] for row in rows)),
        "all_alternate_claims_decided": all(row["alternate_status"] in {"PROVEN_TRUE", "PROVEN_FALSE"} for row in rows),
        "alternate_true_by_namespace": {namespace: sum(row["alternate_status"] == "PROVEN_TRUE" for row in rows if row["namespace"] == namespace) for namespace in ["g6", "q", "g7", "lu"]},
        "rows_detail": rows,
    }
    write_json(audit_root / "MATH_ALTERNATE_VERIFICATION.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run_root.resolve(), args.audit_root.resolve())
    print(json.dumps({"rows": result["rows"], "alternate_status_counts": result["alternate_status_counts"], "all_alternate_claims_decided": result["all_alternate_claims_decided"]}, ensure_ascii=False, indent=2))
    return 0 if result["all_alternate_claims_decided"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
