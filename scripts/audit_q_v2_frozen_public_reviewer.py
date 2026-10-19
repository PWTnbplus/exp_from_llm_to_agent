"""Independent blind symbolic review of the frozen 92-case Q-v2 records."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import sympy as sp

FORBIDDEN = ("private_oracle", "expected_decision", "correct_revised_claim", "hidden_true", "answer_key", "g7_vlu_private")
OPS = {"number", "variable", "add", "sub", "mul", "div", "pow", "neg"}
RELATIONS = {"increasing", "decreasing", "nonincreasing", "nondecreasing"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}: expected object")
            rows.append(value)
    return rows


def has_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(has_forbidden(k) or has_forbidden(v) for k, v in value.items())
    if isinstance(value, list):
        return any(has_forbidden(v) for v in value)
    return isinstance(value, str) and any(term in value.casefold() for term in FORBIDDEN)


def parse_ast(node: Any, variables: set[str]) -> sp.Expr:
    if not isinstance(node, dict) or set(node) - {"op", "value", "name", "args"}:
        raise ValueError("ast_fields")
    op = node.get("op")
    if op not in OPS:
        raise ValueError("ast_op")
    if op == "number":
        value = node.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            raise ValueError("ast_number")
        return sp.Rational(str(value))
    if op == "variable":
        name = node.get("name")
        if not isinstance(name, str) or not name or not name.replace("_", "a").isalnum() or not name[0].isalpha():
            raise ValueError("ast_variable")
        variables.add(name)
        return sp.Symbol(name, real=True)
    args = node.get("args")
    if not isinstance(args, list) or len(args) != (1 if op == "neg" else 2):
        raise ValueError("ast_arity")
    values = [parse_ast(child, variables) for child in args]
    if op == "neg": return -values[0]
    if op == "add": return values[0] + values[1]
    if op == "sub": return values[0] - values[1]
    if op == "mul": return values[0] * values[1]
    if op == "div": return values[0] / values[1]
    return values[0] ** values[1]


def review(candidate: Any) -> tuple[str, str]:
    if not isinstance(candidate, dict): return "NOT_SCORED", "candidate_missing"
    if has_forbidden(candidate): return "NOT_SCORED", "forbidden_material"
    required = {"claim_id", "claim_type", "typed_ast", "assumptions", "quantifiers", "domain", "relation", "time_interval", "origin"}
    if set(candidate) != required: return "NOT_SCORED", "schema_mismatch"
    if candidate.get("claim_type") != "monotonicity" or candidate.get("relation") not in RELATIONS:
        return "INCONCLUSIVE", "unsupported_claim_family"
    variables: set[str] = set()
    try:
        expression = parse_ast(candidate["typed_ast"], variables)
        if len(variables) != 1: return "INCONCLUSIVE", "not_one_variable"
        symbol = sp.Symbol(next(iter(variables)), real=True)
        derivative = sp.simplify(sp.diff(expression, symbol))
        if not derivative.is_number: return "INCONCLUSIVE", "nonconstant_derivative_requires_domain_proof"
        sign = sp.sign(derivative)
        relation = candidate["relation"]
        if sign == 0:
            return ("PASS", "zero_derivative_non_strict") if relation in {"nonincreasing", "nondecreasing"} else ("FAIL", "zero_derivative_strict")
        good = (sign > 0 and relation in {"increasing", "nondecreasing"}) or (sign < 0 and relation in {"decreasing", "nonincreasing"})
        return ("PASS", "constant_derivative_sign") if good else ("FAIL", "constant_derivative_counterexample")
    except Exception as exc:
        return "NOT_SCORED", f"invalid_ast:{type(exc).__name__}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-model-id", default="kimi-k2.5")
    args = parser.parse_args()
    records = read_jsonl(args.records)
    failures: list[str] = []
    case_ids = [row.get("case_id") for row in records]
    if len(records) != 92: failures.append("frozen_case_count_not_92")
    if len(set(case_ids)) != len(case_ids): failures.append("duplicate_case_id")
    counts: Counter[str] = Counter()
    rows = []
    for row in records:
        case_id = row.get("case_id")
        if row.get("model_id") != args.expected_model_id: failures.append(f"model:{case_id}")
        status, reason = review(row.get("candidate"))
        counts[status] += 1
        rows.append({"case_id": case_id, "independent_status": status, "reason": reason})
    result = {
        "schema_version": 1,
        "audit_version": "q-v2-frozen-public-independent-review-v1",
        "reviewer": "separate_ast_sympy_constant_derivative_reviewer",
        "record_count": len(records),
        "status_counts": dict(sorted(counts.items())),
        "records_sha256": hashlib.sha256(args.records.read_bytes()).hexdigest(),
        "private_labels_read": False,
        "truth_key_read": False,
        "pooled_with_frozen_q_v2": False,
        "external_blinded_truth_available": False,
        "domain_grade_review_complete": False,
        "scientific_release_allowed": False,
        "failures": failures,
        "interpretation": "Independent symbolic re-review of frozen public candidates; it cannot establish domain-grade truth accuracy or replace the frozen confirmatory analysis.",
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__": raise SystemExit(main())
