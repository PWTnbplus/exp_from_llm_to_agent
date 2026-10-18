"""Fail-closed Q-v2 structured-claim validation and narrow independent proof.

This module never reads legacy labels, expected decisions, or private oracle
files.  It accepts only a strict typed expression tree and proves a small
whitelisted monotonicity family with SymPy.  Unsupported claims remain
INCONCLUSIVE/NOT_SCORED.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

try:
    import sympy as sp
except ImportError:  # pragma: no cover - the repository test environment has SymPy
    sp = None


FORBIDDEN_TERMS = (
    "expected_decision", "correct_revised_claim", "private_oracle", "oracle_reason",
    "hidden_true", "g7_vlu_private", "u_true", "l_true", "v_true", "answer_key",
)
ALLOWED_CLAIM_TYPES = {"monotonicity", "implication", "equality", "stability", "other_whitelisted"}
ALLOWED_EXPR_OPS = {"number", "variable", "add", "sub", "mul", "div", "pow", "neg"}
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _scan_forbidden(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            folded = str(key).casefold()
            if any(term in folded for term in FORBIDDEN_TERMS):
                hits.append(f"{path}.{key}")
            hits.extend(_scan_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_scan_forbidden(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        folded = value.casefold()
        if any(term in folded for term in FORBIDDEN_TERMS):
            hits.append(path)
    return hits


def _expr(value: Any, variables: set[str]) -> Any:
    if not isinstance(value, dict) or set(value) - {"op", "value", "name", "args"}:
        raise ValueError("typed_ast contains unsupported fields")
    op = value.get("op")
    if op not in ALLOWED_EXPR_OPS:
        raise ValueError("typed_ast contains unsupported operation")
    if op == "number":
        number = value.get("value")
        if not isinstance(number, (int, float)) or isinstance(number, bool) or not math.isfinite(float(number)):
            raise ValueError("typed_ast number must be finite")
        return sp.Float(number) if sp is not None else float(number)
    if op == "variable":
        name = value.get("name")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise ValueError("typed_ast variable is invalid")
        variables.add(name)
        return sp.Symbol(name, real=True) if sp is not None else name
    if op == "neg":
        if set(value) != {"op", "args"} or len(value["args"]) != 1:
            raise ValueError("neg requires one argument")
        return -_expr(value["args"][0], variables)
    args = value.get("args")
    if not isinstance(args, list) or len(args) != 2:
        raise ValueError("binary expression requires two arguments")
    left, right = (_expr(args[0], variables), _expr(args[1], variables))
    if op == "add": return left + right
    if op == "sub": return left - right
    if op == "mul": return left * right
    if op == "div": return left / right
    return left ** right


def validate_candidate(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    required = {"claim_id", "claim_type", "typed_ast", "assumptions", "quantifiers", "domain", "relation", "time_interval", "origin"}
    if set(candidate) != required:
        raise ValueError("candidate schema mismatch")
    if _scan_forbidden(candidate):
        raise ValueError("candidate contains private/oracle material")
    if not isinstance(candidate["claim_id"], str) or not candidate["claim_id"]:
        raise ValueError("claim_id required")
    if candidate["claim_type"] not in ALLOWED_CLAIM_TYPES:
        raise ValueError("claim_type is not whitelisted")
    if candidate["origin"] != "MODEL_GENERATED":
        raise ValueError("candidate origin must be MODEL_GENERATED")
    if not isinstance(candidate["assumptions"], list) or not isinstance(candidate["quantifiers"], list):
        raise ValueError("assumptions and quantifiers must be arrays")
    if not isinstance(candidate["domain"], dict) or not isinstance(candidate["relation"], str):
        raise ValueError("domain and relation are invalid")
    variables: set[str] = set()
    _expr(candidate["typed_ast"], variables)
    if candidate["claim_type"] == "monotonicity" and candidate["relation"] not in {"increasing", "decreasing", "nonincreasing", "nondecreasing"}:
        raise ValueError("unsupported monotonicity relation")
    return {"candidate_sha256": sha256_json(candidate), "variables": sorted(variables)}


def verify_candidate(candidate: Any) -> dict[str, Any]:
    base = {
        "verifier_id": "q-v2-sympy-linear-monotonicity-v1",
        "verifier_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "candidate_claim_hash": None,
        "verdict": "NOT_SCORED",
        "proof_grade": None,
        "reason_code": "CANDIDATE_INVALID",
        "independent_of_tested_model": True,
    }
    try:
        meta = validate_candidate(candidate)
    except ValueError as exc:
        base["reason_code"] = str(exc)
        return base
    base["candidate_claim_hash"] = meta["candidate_sha256"]
    if candidate["claim_type"] != "monotonicity" or sp is None:
        base["verdict"] = "INCONCLUSIVE"
        base["reason_code"] = "UNSUPPORTED_CLAIM_FAMILY"
        return base
    variables: set[str] = set()
    expression = _expr(candidate["typed_ast"], variables)
    if len(variables) != 1:
        base["verdict"] = "INCONCLUSIVE"
        base["reason_code"] = "MULTIVARIABLE_OR_UNBOUNDED_DOMAIN"
        return base
    symbol = sp.Symbol(next(iter(variables)), real=True)
    derivative = sp.simplify(sp.diff(expression, symbol))
    relation = candidate["relation"]
    if derivative.is_number:
        sign = sp.sign(derivative)
        good = (relation in {"decreasing", "nonincreasing"} and sign < 0) or (relation in {"increasing", "nondecreasing"} and sign > 0)
        if good:
            base.update({"verdict": "PASS", "proof_grade": "A", "reason_code": "SYMBOLIC_CONSTANT_DERIVATIVE_SIGN", "proof": f"d/d{symbol}={derivative}"})
        elif sign == 0 and relation.startswith("non"):
            base.update({"verdict": "PASS", "proof_grade": "A", "reason_code": "SYMBOLIC_ZERO_DERIVATIVE_SIGN", "proof": f"d/d{symbol}={derivative}"})
        else:
            base.update({"verdict": "FAIL", "proof_grade": "A", "reason_code": "SYMBOLIC_DERIVATIVE_COUNTEREXAMPLE", "counterexample": f"d/d{symbol}={derivative}"})
        return base
    base["verdict"] = "INCONCLUSIVE"
    base["reason_code"] = "NONCONSTANT_SIGN_REQUIRES_DOMAIN_PROOF"
    return base


def verify_q_record(record: dict[str, Any]) -> dict[str, Any]:
    """Verify Q-v2 evidence without trusting final_decision or self-reported Q."""
    result = {"status": "NOT_SCORED", "reason_code": "CANDIDATE_MISSING", "verifier": None}
    candidate = record.get("candidate")
    evidence = record.get("q_evidence")
    if not isinstance(candidate, dict):
        return result
    try:
        validate_candidate(candidate)
    except ValueError as exc:
        result["reason_code"] = str(exc)
        return result
    if not isinstance(evidence, dict) or evidence.get("checker_requested") is not True:
        result["reason_code"] = "CHECKER_NOT_REQUESTED"
        return result
    if not isinstance(evidence.get("tool_call_ids"), list) or not evidence["tool_call_ids"]:
        result["reason_code"] = "UNOBSERVED_TOOL"
        return result
    if not evidence.get("verifier_input_hash") or not evidence.get("verifier_output_ref"):
        result["reason_code"] = "VERIFIER_EVIDENCE_HASH_MISSING"
        return result
    proof = verify_candidate(candidate)
    return {"status": proof["verdict"], "reason_code": proof["reason_code"], "verifier": proof}
