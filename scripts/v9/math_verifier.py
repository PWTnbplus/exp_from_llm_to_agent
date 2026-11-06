"""V9 deterministic truth generator for the preregistered monotonicity cohort.

The verifier never reads model output and never sends a private truth value to a
model.  It emits an exact SymPy derivative certificate plus a rational check.
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any

import sympy as sp

from .claim_ir import ClaimIR


def _condition(domain: str, x: sp.Symbol) -> Any:
    return {"all_real": True, "x>=0": x >= 0, "x>0": x > 0, "x<=0": x <= 0, "x<0": x < 0}.get(domain, True)


def _samples(domain: str) -> list[Fraction]:
    values = [Fraction(-3), Fraction(-2), Fraction(-1), Fraction(0), Fraction(1), Fraction(2), Fraction(3)]
    if domain in {"x>=0", "x>0"}:
        values = [v for v in values if v >= 0 and (domain != "x>0" or v > 0)]
    if domain in {"x<=0", "x<0"}:
        values = [v for v in values if v <= 0 and (domain != "x<0" or v < 0)]
    return values


def verify_claim(ir: ClaimIR) -> dict[str, Any]:
    x = sp.Symbol(ir.variable, real=True)
    body: dict[str, Any] = {"claim_ir": ir.to_dict(), "verifier": "v9_sympy_exact_derivative_rational_v1"}
    try:
        expr = sp.sympify(ir.expression, locals={"x": x}, evaluate=True)
        derivative = sp.factor(sp.diff(expr, x))
        weak = derivative >= 0 if ir.relation in {"increasing", "nondecreasing"} else derivative <= 0
        strict = derivative > 0 if ir.relation == "increasing" else derivative < 0 if ir.relation == "decreasing" else weak
        cond = _condition(ir.domain, x)
        exact = None
        for target in [strict, weak] if ir.relation in {"increasing", "decreasing"} else [weak]:
            try:
                bad = sp.reduce_inequalities([cond, sp.Not(target)], x) if cond is not True else sp.reduce_inequalities([sp.Not(target)], x)
                if bad is sp.false:
                    exact = True
                    break
            except Exception:
                continue
        witness = None
        for left in _samples(ir.domain):
            for right in _samples(ir.domain):
                if right <= left:
                    continue
                delta = sp.simplify(expr.subs(x, sp.Rational(right.numerator, right.denominator)) - expr.subs(x, sp.Rational(left.numerator, left.denominator)))
                bad = delta <= 0 if ir.relation in {"increasing", "nondecreasing"} else delta >= 0
                if ir.relation in {"increasing", "decreasing"}:
                    bad = delta <= 0 if ir.relation == "increasing" else delta >= 0
                if bool(bad):
                    witness = {"x1": str(left), "x2": str(right), "delta": str(delta)}
                    break
            if witness:
                break
        status = "PROVEN_TRUE" if exact is True else "PROVEN_FALSE" if witness else "UNKNOWN"
        body.update({"status": status, "expression": str(expr), "derivative": str(derivative), "domain": ir.domain, "witness": witness, "solver_status": "EXACT_OR_RATIONAL"})
    except Exception as exc:
        body.update({"status": "UNKNOWN", "solver_status": "ERROR", "error": f"{type(exc).__name__}:{str(exc)[:300]}"})
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["certificate_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return body
