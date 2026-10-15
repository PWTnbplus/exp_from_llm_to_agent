#!/usr/bin/env python3
"""Frozen public-only V mechanism used by the G8 adapter.

The verifier evaluates transparent expressions from ``model_visible`` only.
It deliberately emits calculations and quality flags, never a gold verdict,
expected decision, corrected claim, or private oracle label.  A provider model
must interpret the public evidence and make the final decision.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from typing import Any


VERSION = "g8-public-v-verifier-v1"
_SAFE_NAMES = {"log": math.log, "ln": math.log, "exp": math.exp, "sqrt": math.sqrt,
               "abs": abs, "pow": pow, "pi": math.pi}
_SAFE_NODES = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BinOp, ast.UnaryOp,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
               ast.Call)


def _safe_eval(expression: str, values: dict[str, float]) -> float:
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_NODES):
            raise ValueError(f"unsupported expression node: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_NAMES:
                raise ValueError("unsupported function")
        if isinstance(node, ast.Name) and node.id not in values and node.id not in _SAFE_NAMES:
            raise ValueError(f"unknown public symbol: {node.id}")
    value = eval(compile(tree, "<g8-public-verifier>", "eval"), {"__builtins__": {}},
                 {**_SAFE_NAMES, **values})
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("non-finite result")
    return value


def _public_parameters(problem: str) -> dict[str, float]:
    # The benchmark stores the known public parameter object in the problem
    # statement.  This parser never reads a sibling file or an answer key.
    match = re.search(r"(\{.*\})", problem, flags=re.S)
    if not match:
        return {}
    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    return {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def _intervention_tokens(statement: str) -> list[float]:
    values: list[float] = []
    # These are observations from the public intervention string, not labels.
    for token in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", statement):
        try:
            values.append(float(token))
        except ValueError:
            pass
    return values


def _checks(family: str, values: dict[str, float]) -> list[tuple[str, str]]:
    expressions: dict[str, list[tuple[str, str]]] = {
        "TB-L1-001": [("growth_or_decay_rate", "r"), ("doubling_or_half_time", "log(2)/r")],
        "TB-L1-002": [("origin_slope", "r"), ("carrying_slope", "-r")],
        "TB-L1-003": [("harvested_equilibrium", "(r - h/N0)" )],
        "TB-L1-004": [("basic_reproduction_ratio", "beta/gamma")],
        "TB-L1-005": [("substrate_rate", "Vmax*S/(Km+S+S*S/Ki)")],
        "TB-L1-006": [("occupancy", "S/(K+S)")],
        "TB-L1-007": [("coexistence_ratio", "a/b")],
        "TB-L1-008": [("protein_state_ratio", "alpha/beta")],
        "TB-L1-009": [("on_probability", "kon/(kon+koff)")],
        "TB-L1-011": [("monod_rate", "mumax*S/(Ks+S)"), ("net_growth_rate", "mumax*S/(Ks+S)-D")],
        "TB-L1-012": [("invasion_rate", "-c+d*resident_prey")],
        "TC-L1-001": [("half_life", "log(2)/k")],
        "TC-L1-002": [("second_order_half_life", "1/(k*A0)")],
        "TC-L1-003": [("zero_order_completion_time", "A0/k")],
        "TC-L1-004": [("arrhenius_ratio", "exp(Ea/R*(1/T1-1/T2))")],
        "TC-L1-005": [("equilibrium_constant", "exp(-dG/(R*T))")],
        "TC-L1-006": [("vant_hoff_ratio", "exp(dH/R*(1/T1-1/T2))")],
        "TC-L1-007": [("partition_function", "1+exp(-epsilon_over_RT)")],
        "TC-L1-008": [("capacity_response", "exp(-x)")],
        "TC-L1-009": [("branch_ratio", "kB/kC")],
        "TC-L1-010": [("pseudo_first_order_rate", "k*B")],
        "TC-L1-011": [("buffer_ratio", "10**(pH-pKa)")],
        "TC-L1-012": [("michaelis_menten_rate", "Vmax*S/(Km+S)")],
    }
    return expressions.get(family, [])


def verify_public_case(model_visible: dict[str, Any]) -> dict[str, Any]:
    family = str(model_visible.get("theory_family_id", ""))
    # theory_family_id is public metadata in the G7 request.  It is used only
    # to select a frozen public equation, never to look up a hidden answer.
    if not family:
        family = str(model_visible.get("case_family", ""))
    problem = str(model_visible.get("original_problem", ""))
    values = _public_parameters(problem)
    checks: list[dict[str, Any]] = []
    for name, expression in _checks(family, values):
        try:
            result = _safe_eval(expression, values)
            checks.append({"check_id": name, "expression": expression, "result": result,
                           "finite": True, "source": "public_problem_parameters"})
        except Exception as exc:
            checks.append({"check_id": name, "expression": expression, "finite": False,
                           "error_type": type(exc).__name__, "source": "public_problem_parameters"})
    digest_input = {
        "version": VERSION,
        "family": family,
        "problem": problem,
        "intervention_statement": model_visible.get("intervention_statement", ""),
    }
    return {
        "mechanism_id": "V",
        "verifier_version": VERSION,
        "public_input_sha256": hashlib.sha256(
            json.dumps(digest_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "observable_public_parameters": values,
        "intervention_numeric_tokens": _intervention_tokens(str(model_visible.get("intervention_statement", ""))),
        "checks": checks,
        "quality": {
            "status": "PUBLIC_COMPUTATION_ONLY",
            "non_oracle": True,
            "decision_label_emitted": False,
            "private_answer_loaded": False,
        },
    }


if __name__ == "__main__":
    import sys
    payload = json.load(sys.stdin)
    print(json.dumps(verify_public_case(payload), ensure_ascii=False, sort_keys=True))
