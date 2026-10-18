"""Independent audit of Q blind-truth calibration results."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import sympy as sp

try:
    from scripts.v3.q_v2 import _expr, validate_candidate
except ModuleNotFoundError:  # direct script entry point
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.v3.q_v2 import _expr, validate_candidate


FORBIDDEN = ("private_oracle", "expected_decision", "correct_revised_claim", "hidden_true", "answer_key", "g7_vlu_private")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forbidden(value: Any) -> bool:
    if isinstance(value, dict): return any(forbidden(k) or forbidden(v) for k, v in value.items())
    if isinstance(value, list): return any(forbidden(v) for v in value)
    return isinstance(value, str) and any(term in value.casefold() for term in FORBIDDEN)


def independent_relation(ast: dict[str, Any]) -> set[str]:
    variables: set[str] = set()
    expression = sp.nsimplify(_expr(ast, variables))
    if variables not in ({"x"}, set()):
        raise ValueError("blind truth task must have at most x")
    x = sp.Symbol("x", real=True)
    derivative = sp.Poly(sp.expand(sp.diff(expression, x)), x)
    if derivative.is_zero:
        return {"nonincreasing", "nondecreasing"}
    signs = [sp.sign(coef) for coef in derivative.all_coeffs()]
    if all(sign in (0, 1) for sign in signs):
        return {"increasing", "nondecreasing"}
    if all(sign in (0, -1) for sign in signs):
        return {"decreasing", "nonincreasing"}
    raise ValueError("task derivative does not have a one-sided polynomial sign")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-model-id", default="kimi-k2.5")
    args = parser.parse_args()
    plan = json.loads((args.cohort / "cohort_plan.json").read_text(encoding="utf-8"))
    tasks = {row["task_id"]: row for row in read_jsonl(args.cohort / "public_tasks.jsonl")}
    truth = {row["task_id"]: row for row in read_jsonl(args.cohort / "truth_key.jsonl")}
    records = read_jsonl(args.run / "records.jsonl")
    traces = read_jsonl(args.run / "provider_traces.jsonl")
    failures: list[str] = []
    if sha256(args.cohort / "truth_key.jsonl") != plan["truth_key_sha256"]:
        failures.append("truth_key_hash_mismatch")
    if set(tasks) != set(truth) or len(tasks) != 24:
        failures.append("task_truth_bijection_or_count")
    if len(records) != len(tasks) or {r.get("task_id") for r in records} != set(tasks):
        failures.append("record_task_bijection")
    counts: Counter[str] = Counter()
    row_results = []
    for row in records:
        task_id = row.get("task_id"); task = tasks.get(task_id); key = truth.get(task_id)
        if task is None or key is None: continue
        if row.get("model_id") != args.expected_model_id: failures.append(f"model:{task_id}")
        if row.get("private_labels_read") is not False or row.get("truth_key_read") is not False: failures.append(f"isolation:{task_id}")
        if forbidden(row.get("candidate")): failures.append(f"forbidden_candidate:{task_id}")
        candidate = row.get("candidate")
        status = "NOT_SCORED"
        reason = "missing_or_invalid_candidate"
        if isinstance(candidate, dict):
            try:
                validate_candidate(candidate)
                variables: set[str] = set()
                expression = sp.nsimplify(_expr(candidate["typed_ast"], variables))
                expected_vars: set[str] = set()
                expected_expression = sp.nsimplify(_expr(task["expression"], expected_vars))
                x = sp.Symbol("x", real=True)
                same_expr = variables.issubset({"x"}) and expected_vars.issubset({"x"}) and sp.simplify(expression - expected_expression) == 0
                independently_derived = independent_relation(task["expression"])
                key_relations = set(key["acceptable_relations"])
                if key_relations != independently_derived:
                    failures.append(f"truth_key_derivation_mismatch:{task_id}")
                if not same_expr:
                    status, reason = "AST_MISMATCH", "candidate_expression_differs"
                elif candidate.get("relation") not in independently_derived:
                    status, reason = "WRONG_RELATION", "independent_derivative_sign"
                else:
                    status, reason = "TRUTH_MATCH", "independent_derivative_sign_and_expression_match"
            except Exception as exc:
                reason = str(exc)
        counts[status] += 1
        row_results.append({"task_id": task_id, "status": status, "reason": reason})
        if not any(t.get("task_id") == task_id for t in traces): failures.append(f"trace_missing:{task_id}")
    summary = {
        "schema_version": 1, "audit_version": "q-blind-truth-independent-v1", "task_count": len(tasks),
        "record_count": len(records), "trace_count": len(traces), "status_counts": dict(sorted(counts.items())),
        "task_sha256": sha256(args.cohort / "public_tasks.jsonl"), "truth_key_sha256": sha256(args.cohort / "truth_key.jsonl"),
        "records_sha256": sha256(args.run / "records.jsonl"), "traces_sha256": sha256(args.run / "provider_traces.jsonl"),
        "private_labels_read": False, "truth_key_sent_to_model": False, "pooled_with_frozen_q_v2": False,
        "scientific_release_allowed": False, "failures": failures,
        "interpretation": "Truth matches are an independent public calibration result; they do not replace the frozen Q-v2 92-case confirmatory analysis.",
        "rows": row_results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2)); return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
