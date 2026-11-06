"""Independent bounded rational counterexample checker for the controlled IR."""
from __future__ import annotations

from fractions import Fraction
from typing import Any


def evaluate(node: Any, x: Fraction) -> Fraction:
    kind = node[0]
    if kind == "const": return Fraction(node[1])
    if kind == "var": return x
    if kind == "neg": return -evaluate(node[1], x)
    if kind == "add": return evaluate(node[1], x) + evaluate(node[2], x)
    if kind == "sub": return evaluate(node[1], x) - evaluate(node[2], x)
    if kind == "mul": return evaluate(node[1], x) * evaluate(node[2], x)
    if kind == "pow": return evaluate(node[1], x) ** int(node[2])
    raise ValueError(kind)


def verify(ir: dict[str, Any]) -> dict[str, Any]:
    # This is deliberately not a proof engine: it can produce a concrete
    # counterexample, but a finite grid cannot establish a universal claim.
    samples = [Fraction(i, 2) for i in range(0, 17)]
    values = [(x, evaluate(ir["expression"], x)) for x in samples]
    relation = ir["relation"]
    violations = []
    for (x0, y0), (x1, y1) in zip(values, values[1:]):
        delta = y1 - y0
        if relation in {"increasing", "nondecreasing"} and delta < 0: violations.append((x0, x1, delta))
        if relation in {"decreasing", "nonincreasing"} and delta > 0: violations.append((x0, x1, delta))
    if violations:
        x0, x1, delta = violations[0]
        return {"verifier": "bounded-rational-independent-v1", "result": "COUNTEREXAMPLE", "witness": {"x0": str(x0), "x1": str(x1), "delta": str(delta)}}
    return {"verifier": "bounded-rational-independent-v1", "result": "UNKNOWN", "reason": "finite_grid_cannot_prove_universal_claim"}
