from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from typing import Any


class ClaimParseError(ValueError):
    pass


_ALLOWED_NAMES = {"x"}


class _Safe(ast.NodeVisitor):
    allowed = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.UnaryOp, ast.UAdd, ast.USub,
               ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, self.allowed):
            raise ClaimParseError(f"unsafe:{type(node).__name__}")
        super().generic_visit(node)


def safe_expr(value: str) -> str:
    value = value.strip().replace("^", "**")
    if not re.fullmatch(r"[A-Za-z0-9_+*/().\- ]+", value):
        raise ClaimParseError("unsafe_expression")
    tree = ast.parse(value, mode="eval")
    _Safe().visit(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in _ALLOWED_NAMES:
            raise ClaimParseError(f"unknown_name:{node.id}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ClaimParseError("non_numeric_constant")
    return value


@dataclass(frozen=True)
class ClaimIR:
    kind: str
    expression: str
    relation: str
    variable: str
    domain: str
    source_excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_claim(text: str) -> ClaimIR:
    if not text or not text.strip():
        raise ClaimParseError("missing_source_text")
    normalized = " ".join(text.split())
    relation_match = re.search(r"\b(non[- ]?decreasing|non[- ]?increasing|increasing|decreasing)\b", normalized, re.I)
    formula_match = re.search(r"(?:f\s*\(\s*x\s*\)|y)\s*=\s*([A-Za-z0-9_+*/().\- ]+?)\s+is\s+", normalized, re.I)
    if not relation_match or not formula_match:
        raise ClaimParseError("unsupported_claim_pattern")
    relation = relation_match.group(1).lower().replace(" ", "").replace("-", "")
    expression = safe_expr(formula_match.group(1).strip())
    domain_match = re.search(r"(?:for|on|when)\s+(x\s*(?:>=|>|<=|<)\s*-?\d+(?:\.\d+)?)", normalized, re.I)
    domain = domain_match.group(1).replace(" ", "") if domain_match else "all_real"
    return ClaimIR("monotonicity", expression, relation, "x", domain, normalized[:600])
