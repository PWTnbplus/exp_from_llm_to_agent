"""Independent, truth-first certificates for the V10 monotonicity cohort.

The public plan is generated without reading model output.  Certificates are
generated before any provider call and replayed by a second implementation in
the audit process.
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp


FAMILIES: tuple[tuple[str, str, str, str], ...] = (
    ("V10-F01", "x+2", "increasing", "all_real"),
    ("V10-F02", "-x**2", "decreasing", "x>=0"),
    ("V10-F03", "x**2", "increasing", "x>=0"),
    ("V10-F04", "3-2*x", "decreasing", "all_real"),
)
Q_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("V10-Q01", "x+2", "increasing", "all_real"),
    ("V10-Q02", "-x**2", "decreasing", "x>=0"),
    ("V10-Q03", "x**2", "increasing", "x>=0"),
    ("V10-Q04", "3-2*x", "decreasing", "all_real"),
    ("V10-Q05", "x+2", "decreasing", "all_real"),
    ("V10-Q06", "-x**2", "increasing", "x>=0"),
    ("V10-Q07", "x**2", "decreasing", "x>=0"),
    ("V10-Q08", "3-2*x", "increasing", "all_real"),
)


def sha_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _condition(domain: str, x: sp.Symbol) -> Any:
    return {"all_real": True, "x>=0": x >= 0, "x>0": x > 0, "x<=0": x <= 0, "x<0": x < 0}.get(domain, True)


def _samples(domain: str) -> list[Fraction]:
    values = [Fraction(-3), Fraction(-2), Fraction(-1), Fraction(0), Fraction(1), Fraction(2), Fraction(3)]
    if domain in {"x>=0", "x>0"}:
        values = [v for v in values if v >= 0 and (domain != "x>0" or v > 0)]
    if domain in {"x<=0", "x<0"}:
        values = [v for v in values if v <= 0 and (domain != "x<0" or v < 0)]
    return values


def _bad_delta(relation: str, delta: Any) -> bool:
    if relation in {"increasing", "nondecreasing"}:
        return bool(delta <= 0 if relation == "increasing" else delta < 0)
    return bool(delta >= 0 if relation == "decreasing" else delta > 0)


def certificate(expression: str, relation: str, domain: str, *, source: str = "v10_truth_first") -> dict[str, Any]:
    """Return an exact certificate without consulting any model result."""
    x = sp.Symbol("x", real=True)
    body: dict[str, Any] = {"expression": expression, "relation": relation, "domain": domain, "verifier": source}
    try:
        expr = sp.sympify(expression, locals={"x": x}, evaluate=True)
        derivative = sp.factor(sp.diff(expr, x))
        strict = derivative > 0 if relation == "increasing" else derivative < 0 if relation == "decreasing" else derivative >= 0 if relation == "nondecreasing" else derivative <= 0
        cond = _condition(domain, x)
        exact = False
        solver_trace: list[str] = []
        try:
            bad_region = sp.reduce_inequalities([cond, sp.Not(strict)], x) if cond is not True else sp.reduce_inequalities([sp.Not(strict)], x)
            exact = bad_region is sp.false
            solver_trace.append(f"sympy_reduce_inequalities={bad_region}")
        except Exception as exc:
            solver_trace.append(f"sympy_exception={type(exc).__name__}")
        witness = None
        for left in _samples(domain):
            for right in _samples(domain):
                if right <= left:
                    continue
                delta = sp.simplify(expr.subs(x, sp.Rational(right.numerator, right.denominator)) - expr.subs(x, sp.Rational(left.numerator, left.denominator)))
                if _bad_delta(relation, delta):
                    witness = {"x1": str(left), "x2": str(right), "delta": str(delta)}
                    break
            if witness:
                break
        status = "PROVEN_TRUE" if exact else "PROVEN_FALSE" if witness else "UNKNOWN"
        body.update({"status": status, "sympy_expression": str(expr), "derivative": str(derivative), "solver_trace": solver_trace, "witness": witness, "numeric_method": "exact_rational_sample_replay"})
    except Exception as exc:
        body.update({"status": "UNKNOWN", "solver_trace": [f"error={type(exc).__name__}:{str(exc)[:200]}"], "witness": None, "numeric_method": "not_applicable"})
    unsigned = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["certificate_sha256"] = hashlib.sha256(unsigned.encode("utf-8")).hexdigest()
    return body


def replay_certificate(expression: str, relation: str, domain: str) -> dict[str, Any]:
    """Independent replay using derivative sign plus rational witnesses."""
    x = sp.Symbol("x", real=True)
    try:
        expr = sp.sympify(expression, locals={"x": x}, evaluate=True)
        derivative = sp.factor(sp.diff(expr, x))
        cond = _condition(domain, x)
        target = derivative > 0 if relation == "increasing" else derivative < 0 if relation == "decreasing" else derivative >= 0 if relation == "nondecreasing" else derivative <= 0
        bad = sp.reduce_inequalities([cond, sp.Not(target)], x) if cond is not True else sp.reduce_inequalities([sp.Not(target)], x)
        if bad is sp.false:
            return {"status": "PROVEN_TRUE", "derivative": str(derivative), "replay": "independent_sympy_path"}
        for a in _samples(domain):
            for b in _samples(domain):
                if b <= a:
                    continue
                delta = sp.simplify(expr.subs(x, sp.Rational(b.numerator, b.denominator)) - expr.subs(x, sp.Rational(a.numerator, a.denominator)))
                if _bad_delta(relation, delta):
                    return {"status": "PROVEN_FALSE", "derivative": str(derivative), "witness": {"x1": str(a), "x2": str(b), "delta": str(delta)}, "replay": "independent_rational_counterexample_path"}
        return {"status": "UNKNOWN", "derivative": str(derivative), "replay": "independent_path_exhausted"}
    except Exception as exc:
        return {"status": "UNKNOWN", "replay": f"error={type(exc).__name__}"}


def write_certificate(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
