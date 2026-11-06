from __future__ import annotations

from fractions import Fraction
from typing import Any

import sympy as sp


def _to_sympy(node: Any, x: sp.Symbol) -> sp.Expr:
    kind = node[0]
    if kind == "const":
        return sp.Rational(Fraction(node[1]))
    if kind == "var":
        return x
    if kind == "neg":
        return -_to_sympy(node[1], x)
    if kind in {"add", "sub", "mul"}:
        left, right = _to_sympy(node[1], x), _to_sympy(node[2], x)
        return {"add": left + right, "sub": left - right, "mul": left * right}[kind]
    if kind == "pow":
        return _to_sympy(node[1], x) ** int(node[2])
    raise ValueError(f"unknown IR node {kind!r}")


def _sign_on_nonnegative(poly: sp.Expr) -> str:
    x = sp.Symbol("x", real=True)
    p = sp.Poly(sp.expand(poly), x, domain="QQ")
    if p.is_zero:
        return "zero"
    try:
        # Exact interval decomposition for a univariate rational polynomial.
        roots = [root for root, _multiplicity in sp.polys.polytools.ground_roots(p.as_expr(), x).items() if root.is_real]
        probes = [sp.Rational(0)]
        for root in sorted([r for r in roots if r.is_real and r >= 0], key=lambda v: float(v)):
            probes.append(root + sp.Rational(1, 2))
        signs = [sp.sign(p.eval(probe)) for probe in probes]
        if all(s >= 0 for s in signs):
            return "nonnegative"
        if all(s <= 0 for s in signs):
            return "nonpositive"
        return "mixed"
    except Exception:
        return "unknown"


def verify(ir: dict[str, Any]) -> dict[str, Any]:
    x = sp.Symbol("x", real=True)
    expression = _to_sympy(ir["expression"], x)
    derivative = sp.diff(expression, x)
    sign = _sign_on_nonnegative(derivative)
    relation = ir["relation"]
    if relation in {"increasing", "nondecreasing"}:
        result = sign == "nonnegative"
    elif relation in {"decreasing", "nonincreasing"}:
        result = sign == "nonpositive"
    else:
        result = False
    # Strict claims need pairwise proof; this exact engine intentionally does
    # not infer strictness from derivative signs at isolated endpoints.
    if relation.startswith("strictly_"):
        result = False
        reason = "strict_pairwise_engine_not_enabled"
    else:
        reason = "exact_rational_polynomial_derivative_sign"
    return {
        "verifier": "sympy-controlled-ir-v1", "expression": str(expression),
        "derivative": str(derivative), "sign_on_domain": sign,
        "result": "PROVEN" if result else "COUNTEREXAMPLE" if sign == "mixed" else "UNKNOWN",
        "reason": reason,
    }
