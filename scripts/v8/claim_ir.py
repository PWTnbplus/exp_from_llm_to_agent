"""Small, auditable intermediate representation for recoverable math claims.

This parser is intentionally conservative.  It only accepts a tiny expression
language and never invents a proposition when the historical text is absent.
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from typing import Any


_SAFE_EXPR = re.compile(r"^[A-Za-z0-9_+\-*/^()., <>=]+$")


class UnsafeExpression(ValueError):
    pass


class _Validator(ast.NodeVisitor):
    allowed = (
        ast.Expression,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.UnaryOp,
        ast.UAdd,
        ast.USub,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.Tuple,
    )

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, self.allowed):
            raise UnsafeExpression(type(node).__name__)
        super().generic_visit(node)


def safe_expression(text: str) -> str:
    text = text.strip().replace("^", "**")
    if not text or not _SAFE_EXPR.fullmatch(text):
        raise UnsafeExpression(text)
    tree = ast.parse(text, mode="eval")
    _Validator().visit(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in {
            "x",
            "t",
            "A",
            "N",
            "k",
            "r",
            "K",
            "a",
            "b",
        }:
            raise UnsafeExpression(node.id)
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise UnsafeExpression(repr(node.value))
    return text


@dataclass(frozen=True)
class ClaimIR:
    kind: str
    relation: str | None = None
    expression: str | None = None
    variable: str | None = None
    domain: str | None = None
    parameters: dict[str, str] | None = None
    source_excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _relation(text: str) -> str | None:
    lower = text.lower()
    if re.search(r"\bnon[- ]?decreasing\b", lower):
        return "nondecreasing"
    if re.search(r"\bnon[- ]?increasing\b", lower):
        return "nonincreasing"
    if re.search(r"\b(strictly\s+)?increasing\b|\bmonotonically\s+increasing\b", lower):
        return "increasing"
    if re.search(r"\b(strictly\s+)?decreasing\b|\bmonotonically\s+decreasing\b", lower):
        return "decreasing"
    return None


def parse_claim_text(text: str | None) -> tuple[ClaimIR | None, str]:
    """Recover a claim only when a public proposition is actually present."""

    if not text or not text.strip():
        return None, "MISSING_SOURCE_TEXT"
    text = " ".join(text.split())
    relation = _relation(text)
    formula = re.search(
        r"(?:f\s*\(\s*x\s*\)|y|g\s*\(\s*x\s*\))\s*=\s*([0-9A-Za-z_+*/^(). -]+?)(?:\s+is\s+|\s*,|\s+for\s+|$)",
        text,
        flags=re.I,
    )
    if relation and formula:
        try:
            expression = safe_expression(formula.group(1).rstrip())
        except (SyntaxError, ValueError, UnsafeExpression):
            return None, "UNSAFE_OR_UNPARSEABLE_EXPRESSION"
        domain_match = re.search(
            r"(?:for|when|on)\s+(x\s*(?:>=|>|<=|<)\s*[-+]?\d+(?:\.\d+)?)",
            text,
            flags=re.I,
        )
        domain = domain_match.group(1).replace(" ", "") if domain_match else "all_real"
        return ClaimIR(
            kind="monotonicity",
            relation=relation,
            expression=expression,
            variable="x",
            domain=domain,
            source_excerpt=text[:500],
        ), "RECOVERED"

    ode = re.search(
        r"d\s*([A-Za-z])\s*/\s*d\s*t\s*=\s*([-+]?\s*[A-Za-z0-9().*/^ ]+)",
        text,
        flags=re.I,
    )
    if ode and re.search(r"(?:k|r)\s*>\s*0", text, flags=re.I):
        variable = ode.group(1)
        try:
            expression = safe_expression(ode.group(2).strip())
        except (SyntaxError, ValueError, UnsafeExpression):
            return None, "UNSAFE_OR_UNPARSEABLE_ODE"
        return ClaimIR(
            kind="ode_sign",
            relation=relation,
            expression=expression,
            variable=variable,
            domain="positive_initial_state",
            parameters={"positive_parameter": "k_or_r"},
            source_excerpt=text[:500],
        ), "RECOVERED"

    return None, "NO_SUPPORTED_CLAIM_PATTERN"

