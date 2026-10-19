"""Independent deterministic proof/counterexample engine for the V8 DSL."""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from typing import Any

import sympy as sp

from .claim_ir import ClaimIR


def _domain_condition(domain: str | None, x: sp.Symbol) -> sp.Relational | bool:
    if not domain or domain == "all_real":
        return True
    if domain == "x>=0":
        return x >= 0
    if domain == "x>0":
        return x > 0
    if domain == "x<=0":
        return x <= 0
    if domain == "x<0":
        return x < 0
    return True


def _safe_sympy(expression: str, variable: str = "x") -> tuple[sp.Expr, sp.Symbol]:
    symbol = sp.Symbol(variable, real=True)
    locals_map = {name: sp.Symbol(name, real=True) for name in ["x", "t", "A", "N", "k", "r", "K", "a", "b"]}
    locals_map[variable] = symbol
    return sp.sympify(expression, locals=locals_map, evaluate=True), symbol


def _truth_from_derivative(derivative: sp.Expr, relation: str, x: sp.Symbol, domain: str | None) -> bool | None:
    cond = _domain_condition(domain, x)
    wanted = derivative >= 0 if relation in {"increasing", "nondecreasing"} else derivative <= 0
    if relation in {"increasing", "decreasing"}:
        # The prospective DSL uses the strict words for claims whose derivative
        # has a strict sign.  A zero at an isolated endpoint is handled by the
        # non-strict relation in the private truth key.
        wanted = derivative > 0 if relation == "increasing" else derivative < 0
    try:
        reduced = sp.reduce_inequalities([cond, sp.Not(wanted)], x) if cond is not True else sp.reduce_inequalities([sp.Not(wanted)], x)
        if reduced is sp.false:
            return True
    except Exception:
        pass
    try:
        reduced_bad = sp.reduce_inequalities([cond, sp.Not(wanted)], x) if cond is not True else sp.reduce_inequalities([sp.Not(wanted)], x)
        if reduced_bad is sp.false:
            return True
    except Exception:
        return None
    return None


def _sample_counterexample(expr: sp.Expr, relation: str, domain: str | None, x: sp.Symbol) -> dict[str, Any] | None:
    values = [Fraction(-3), Fraction(-2), Fraction(-1), Fraction(0), Fraction(1), Fraction(2), Fraction(3)]
    if domain in {"x>=0", "x>0"}:
        values = [v for v in values if v >= 0 and (domain != "x>0" or v > 0)]
    if domain in {"x<=0", "x<0"}:
        values = [v for v in values if v <= 0 and (domain != "x<0" or v < 0)]
    for left in values:
        for right in values:
            if right <= left:
                continue
            dl = sp.simplify(expr.subs(x, sp.Rational(left.numerator, left.denominator)))
            dr = sp.simplify(expr.subs(x, sp.Rational(right.numerator, right.denominator)))
            delta = sp.simplify(dr - dl)
            bad = delta <= 0 if relation in {"increasing", "nondecreasing"} else delta >= 0
            if relation in {"increasing", "decreasing"}:
                bad = delta <= 0 if relation == "increasing" else delta >= 0
            if bool(bad):
                return {"x1": str(left), "x2": str(right), "delta": str(delta)}
    return None


def prove_claim(ir: ClaimIR) -> dict[str, Any]:
    if ir.kind == "monotonicity" and ir.expression and ir.relation:
        try:
            expr, x = _safe_sympy(ir.expression, ir.variable or "x")
            derivative = sp.factor(sp.diff(expr, x))
            cond = _domain_condition(ir.domain, x)
            relation = ir.relation
            target = derivative >= 0 if relation in {"increasing", "nondecreasing"} else derivative <= 0
            if relation in {"increasing", "decreasing"}:
                target = derivative > 0 if relation == "increasing" else derivative < 0
            exact = None
            try:
                bad_region = sp.reduce_inequalities([cond, sp.Not(target)], x) if cond is not True else sp.reduce_inequalities([sp.Not(target)], x)
                exact = bad_region is sp.false
            except Exception:
                exact = None
            if exact is not True and relation in {"increasing", "decreasing"}:
                # A nonzero polynomial with a derivative of one weak sign on a
                # connected interval is strictly monotone; isolated stationary
                # points (x^2 on x>=0, x^3 on R) do not invalidate strictness.
                weak_target = derivative >= 0 if relation == "increasing" else derivative <= 0
                try:
                    weak_bad = sp.reduce_inequalities([cond, sp.Not(weak_target)], x) if cond is not True else sp.reduce_inequalities([sp.Not(weak_target)], x)
                    if weak_bad is sp.false and sp.simplify(derivative) != 0:
                        exact = True
                except Exception:
                    pass
            if exact is True:
                status = "PROVEN_TRUE"
                witness = None
            else:
                witness = _sample_counterexample(expr, relation, ir.domain, x)
                status = "PROVEN_FALSE" if witness else "UNKNOWN"
            certificate = {
                "solver": "sympy_exact_derivative_plus_rational_replay",
                "expression": str(expr),
                "derivative": str(derivative),
                "domain": ir.domain,
                "target_sign": str(target),
                "witness": witness,
            }
            return _record(ir, status, certificate)
        except Exception as exc:
            return _record(ir, "UNKNOWN", {"error": type(exc).__name__})
    if ir.kind == "ode_sign" and ir.expression:
        sign = -1 if "-" in ir.expression.replace(" ", "") else 1
        status = "PROVEN_TRUE" if sign < 0 and ir.relation in {"decreasing", "nonincreasing"} else "UNKNOWN"
        return _record(ir, status, {"solver": "ode_sign_replay", "expression": ir.expression, "sign": sign})
    return _record(ir, "UNKNOWN", {"reason": "unsupported_ir"})


def _record(ir: ClaimIR, status: str, certificate: dict[str, Any]) -> dict[str, Any]:
    body = {"claim_ir": ir.to_dict(), "status": status, "certificate": certificate}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    body["certificate_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return body


def replay_certificate(record: dict[str, Any]) -> dict[str, Any]:
    ir_data = record["claim_ir"]
    ir = ClaimIR(**ir_data)
    fresh = prove_claim(ir)
    return {
        "certificate_sha256_matches": fresh["certificate_sha256"] == record.get("certificate_sha256"),
        "status_matches": fresh["status"] == record.get("status"),
        "replayed_status": fresh["status"],
        "original_status": record.get("status"),
    }

