"""A small non-evaluating DSL for polynomial monotonicity claims.

Only a Python expression AST containing x, rational/float constants and the
four arithmetic operators is accepted.  The AST is converted to a tuple IR;
untrusted text is never passed to eval or sympy.sympify.
"""
from __future__ import annotations

import ast
import re
from fractions import Fraction
from typing import Any


class ClaimParseError(ValueError):
    pass


def _number(node: ast.Constant) -> str:
    if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
        raise ClaimParseError("only finite numeric constants are allowed")
    if isinstance(node.value, float) and (node.value != node.value or abs(node.value) == float("inf")):
        raise ClaimParseError("non-finite numeric constant")
    return str(Fraction(str(node.value)))


def _expr(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return ("const", _number(node))
    if isinstance(node, ast.Name) and node.id == "x":
        return ("var", "x")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return ("neg", _expr(node.operand)) if isinstance(node.op, ast.USub) else _expr(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Pow)):
        if isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant) or not isinstance(node.right.value, int) or not 0 <= node.right.value <= 8:
                raise ClaimParseError("power must be an integer in [0,8]")
            return ("pow", _expr(node.left), int(node.right.value))
        op = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul"}[type(node.op)]
        return (op, _expr(node.left), _expr(node.right))
    raise ClaimParseError(f"unsupported expression node: {type(node).__name__}")


def parse_expression(text: str) -> Any:
    tree = ast.parse(text.strip(), mode="eval")
    return _expr(tree.body)


def parse_claim(text: str) -> dict[str, Any]:
    normalized = text.replace("−", "-").replace("≤", "<=").replace("≥", ">=")
    # The public task dialect uses ^ for powers; it is normalized before the
    # controlled Python AST parser sees it.  No arbitrary code is introduced.
    normalized = normalized.replace("^", "**")
    match = re.search(r"f\s*\(\s*x\s*\)\s*=\s*(.+?)\s+is\s+(strictly\s+)?(increasing|decreasing|nondecreasing|nonincreasing)\s+for\s+x\s*>=\s*0\s*$", normalized, re.I)
    if not match:
        raise ClaimParseError("expected f(x)=POLY is RELATION for x>=0")
    relation = match.group(3).lower()
    if match.group(2):
        relation = "strictly_" + relation
    return {
        "dsl": "polynomial_monotonicity_v1", "expression_text": match.group(1).strip(),
        "expression": parse_expression(match.group(1)), "relation": relation,
        "domain": {"variable": "x", "lower": "0", "lower_inclusive": True, "upper": None},
    }


def parse_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    claim = candidate.get("claim")
    if not isinstance(claim, str):
        raise ClaimParseError("candidate claim is missing")
    return parse_claim(claim)
