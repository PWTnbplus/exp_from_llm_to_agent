#!/usr/bin/env python3
"""Reconcile failed G2/G3 matrix rows without changing raw benchmark data.

The matrix runner stores ``answer_correct=false`` in the default failure
validation object.  That flag is not an answer judgment when the run failed
before a candidate was submitted.  This audit therefore uses the persisted
run/status/trace evidence first and only calls the local private evaluator for
an output that was already present in a raw result or provider trace.

No provider is called, no hidden answer is copied to the report, and no raw
result is modified.  Failed rows remain failures even when a visible payload
is independently judged to be wrong; that judgment is recorded separately
and is never added to the ordinary answer-error denominator.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

# Running a script by path puts ``scripts/`` (rather than the repository
# root) on sys.path.  Add the root so the existing conservative JSON extractor
# can be reused both from pytest and as a command-line script.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_repair_g5_answer_given import extract_json_object
from src.scientific_discovery.theory_benchmark.verification import verify_candidate


GROUPS = ("G2", "G3")
TIMEOUT_RE = re.compile(r"(?i)timeout|timed?\s*out|deadline exceeded|read timed out")
ACCESS_RE = re.compile(r"(?i)\b(?:401|403)\b|forbidden|unauthorized|permission denied")
PROVIDER_RE = re.compile(r"(?i)provider|http\s*error|connection|rate.?limit|bad gateway|service unavailable|api request")
PARSE_RE = re.compile(r"(?i)jsondecodeerror|json decode|invalid json|expecting .*delimiter|parse")
POLICY_RE = re.compile(r"(?i)policy|budget|violation|unauthorized tool|contamination")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def error_only(value: Any) -> bool:
    """Return true for the runner's synthetic exception payload, not answers."""
    if not isinstance(value, dict):
        return True
    nested = value.get("final_answer")
    if isinstance(nested, dict):
        return error_only(nested) if set(nested).issubset({"error", "message", "type"}) else False
    return "error" in value and set(value).issubset({"error", "message", "type"})


def response_contents(result: dict[str, Any]) -> Iterable[tuple[str, int | None, str]]:
    trace = (result.get("metadata") or {}).get("provider_trace")
    if not isinstance(trace, list):
        return
    for item_index, item in enumerate(trace):
        if not isinstance(item, dict):
            continue
        response = item.get("response")
        if not isinstance(response, dict):
            continue
        content = response.get("content")
        if isinstance(content, str) and content.strip():
            yield ("provider_trace", item.get("call_index", item_index), content)


def find_raw_result(run_dir: Path, group: str, model_id: str, task_id: str, ledger_path: str | None) -> Path | None:
    if ledger_path:
        candidate = Path(ledger_path)
        if candidate.is_file():
            return candidate
    model_dir = run_dir / "models" / model_id
    matches = sorted(model_dir.glob(f"{group}__{task_id}__*.json"))
    return matches[0] if matches else None


def trace_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    validation = result.get("validation")
    if isinstance(validation, dict):
        parts.extend(str(x) for x in validation.get("errors", []) if x is not None)
    answer = result.get("answer")
    if isinstance(answer, dict):
        parts.extend(str(answer.get(key, "")) for key in ("error", "message", "type"))
    provider_trace = (result.get("metadata") or {}).get("provider_trace")
    if isinstance(provider_trace, list):
        for item in provider_trace:
            if not isinstance(item, dict):
                continue
            for key in ("error", "exception", "message"):
                if item.get(key) is not None:
                    parts.append(str(item[key]))
            error = item.get("error")
            if isinstance(error, dict):
                parts.extend(str(error.get(key, "")) for key in ("type", "message", "status"))
    return " ".join(parts)


def failure_class(result: dict[str, Any], *, has_response: bool) -> str:
    raw_status = result.get("status")
    validation = result.get("validation") or {}
    validation_status = validation.get("status") if isinstance(validation, dict) else None
    if raw_status == "COMPLETED":
        if validation_status == "PASS" and validation.get("answer_correct") is True:
            return "ANSWER_CORRECT"
        if validation_status == "MODEL_ERROR" and not error_only(result.get("answer")):
            return "ANSWER_WRONG"
        return "COMPLETED_INVALID_OR_UNJUDGED"
    text = trace_text(result)
    if TIMEOUT_RE.search(text):
        return "FAILED_TIMEOUT"
    if ACCESS_RE.search(text):
        return "FAILED_PROVIDER_ACCESS"
    if POLICY_RE.search(text):
        return "FAILED_POLICY_OR_BUDGET"
    if PARSE_RE.search(text) or validation_status == "MODEL_ERROR" and has_response:
        return "FAILED_OUTPUT_PARSE_OR_MODEL_FORMAT"
    if PROVIDER_RE.search(text) or not has_response:
        return "FAILED_PROVIDER_OR_MODEL_ERROR"
    return "FAILED_OTHER"


def candidate_from_result(result: dict[str, Any]) -> tuple[str, int | None, dict[str, Any]] | None:
    answer = result.get("answer")
    if isinstance(answer, dict) and not error_only(answer):
        return ("raw_result.answer", None, answer)
    candidates: list[tuple[str, int | None, dict[str, Any]]] = []
    for source, call_index, content in response_contents(result):
        parsed = extract_json_object(content)
        if isinstance(parsed, dict) and not error_only(parsed):
            candidates.append((source, call_index, parsed))
    return candidates[-1] if candidates else None


def audit_row(row: dict[str, Any], run_dir: Path, data_dir: Path) -> dict[str, Any]:
    group = str(run_dir.parent.name)
    task_id = str(row.get("task_id"))
    model_id = str(row.get("model_id"))
    raw_path = find_raw_result(run_dir, group, model_id, task_id, row.get("raw_result_path"))
    base: dict[str, Any] = {
        "group": group,
        "model_id": model_id,
        "task_id": task_id,
        "ledger_state": row.get("state"),
        "raw_status": row.get("raw_status"),
        "validation_status": row.get("validation_status"),
        "raw_result_present": raw_path is not None,
        "raw_result_sha256": None,
        "raw_result_path": str(raw_path) if raw_path else None,
        "failure_class": None,
        "candidate_source": None,
        "candidate_call_index": None,
        "candidate_sha256": None,
        "independent_evaluation": None,
        "answer_correct": None,
        "counted_as_wrong": False,
    }
    if raw_path is None:
        base["failure_class"] = "MISSING_RAW_RESULT"
        return base
    base["raw_result_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    try:
        result = load_json(raw_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        base["failure_class"] = "RAW_RESULT_UNREADABLE"
        base["independent_evaluation"] = type(exc).__name__
        return base
    if not isinstance(result, dict):
        base["failure_class"] = "RAW_RESULT_NOT_OBJECT"
        return base
    has_response = any(True for _ in response_contents(result))
    base["failure_class"] = failure_class(result, has_response=has_response)
    validation = result.get("validation") or {}
    if base["failure_class"] == "ANSWER_CORRECT":
        base["answer_correct"] = True
        return base
    if base["failure_class"] == "ANSWER_WRONG":
        base["answer_correct"] = False
        base["counted_as_wrong"] = True
        return base
    candidate = candidate_from_result(result)
    if candidate is None:
        if base["failure_class"].startswith("FAILED"):
            base["independent_evaluation"] = "NO_SUBMITTED_PAYLOAD"
        return base
    source, call_index, payload = candidate
    base["candidate_source"] = source
    base["candidate_call_index"] = call_index
    base["candidate_sha256"] = sha256_json(payload)
    checked = verify_candidate(task_id, payload, data_dir=data_dir, redact_errors=True)
    base["independent_evaluation"] = checked.get("status")
    base["answer_correct"] = checked.get("answer_correct") if isinstance(checked, dict) else None
    # A failed request stays outside the ordinary wrong-answer count.  This is
    # deliberately separate even when a visible failed payload is evaluable.
    if base["failure_class"].startswith("FAILED"):
        if checked.get("status") == "PASS":
            base["failure_class"] = "FAILED_RECOVERED_CORRECT"
        elif checked.get("status") == "MODEL_ERROR":
            base["failure_class"] = "FAILED_WITH_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED"
    elif base["failure_class"] == "COMPLETED_INVALID_OR_UNJUDGED":
        base["independent_evaluation"] = checked.get("status")
    return base


def discover_runs(root: Path) -> Iterable[tuple[str, Path, dict[str, Any]]]:
    for group in GROUPS:
        for run_dir in sorted((root / group).glob("*") if (root / group).is_dir() else []):
            ledger_path = run_dir / "matrix_completion_ledger.json"
            if not run_dir.is_dir() or not ledger_path.is_file():
                continue
            ledger = load_json(ledger_path)
            if isinstance(ledger, dict) and isinstance(ledger.get("rows"), list):
                yield group, run_dir, ledger


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_group: dict[str, dict[str, Any]] = {}
    for group in GROUPS:
        subset = [row for row in records if row["group"] == group]
        counts = Counter(row["failure_class"] for row in subset)
        model_counts: dict[str, dict[str, int]] = {}
        for model in sorted({row["model_id"] for row in subset}):
            model_counts[model] = dict(sorted(Counter(row["failure_class"] for row in subset if row["model_id"] == model).items()))
        by_group[group] = {"row_count": len(subset), "failure_class_counts": dict(sorted(counts.items())), "by_model": model_counts}
    return {"row_count": len(records), "by_group": by_group}


def markdown(summary: dict[str, Any], records: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# G2/G3 failure reconciliation",
        "",
        f"> Generated at {generated_at}. This is a read-only derived audit; raw results and traces were not modified and no provider request was made.",
        "",
        "## Interpretation rule",
        "",
        "`FAILED`, `FAILED_TIMEOUT`, provider/access errors, policy/budget violations, parse failures, and `MISSING_RAW_RESULT` are failures—not wrong answers. The runner's default `validation.answer_correct=false` is ignored for those rows. Only a raw `COMPLETED` record with a real submitted payload and `validation.status=MODEL_ERROR` is counted as `ANSWER_WRONG`.",
        "",
        "A failed row with an already persisted response is locally checked only as a separate diagnostic. Even when that payload is judged wrong, it remains outside the normal wrong-answer count. A failed row is locally recoverable only when the persisted response contains a parseable candidate and the private evaluator returns `PASS`; no output is invented.",
        "",
        "## Summary",
        "",
        "| Group | Rows | Correct | Wrong (completed only) | Failed / unproven | Missing raw | Failed payload locally correct | Failed payload locally wrong (not counted) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in GROUPS:
        counts = summary["by_group"].get(group, {}).get("failure_class_counts", {})
        failed = sum(value for key, value in counts.items() if key.startswith("FAILED"))
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            group,
            summary["by_group"].get(group, {}).get("row_count", 0),
            counts.get("ANSWER_CORRECT", 0),
            counts.get("ANSWER_WRONG", 0),
            failed,
            counts.get("MISSING_RAW_RESULT", 0),
            counts.get("FAILED_RECOVERED_CORRECT", 0),
            counts.get("FAILED_WITH_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED", 0),
        ))
    lines += [
        "",
        "## Failure classes",
        "",
        "| Group | Class | Count | Meaning |",
        "|---|---|---:|---|",
    ]
    meanings = {
        "ANSWER_CORRECT": "Completed and independently recorded PASS.",
        "ANSWER_WRONG": "Completed with a real payload independently recorded MODEL_ERROR; included in wrong-answer counts.",
        "MISSING_RAW_RESULT": "No raw result artifact exists; no synthetic row was created.",
        "FAILED_RECOVERED_CORRECT": "Failed run, but an already persisted response yielded a parseable candidate independently verified PASS.",
        "FAILED_WITH_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED": "Failed run with an already persisted candidate evaluated as mismatch; retained as failure and excluded from ordinary wrong counts.",
        "FAILED_OUTPUT_PARSE_OR_MODEL_FORMAT": "A model response existed, but the runner could not parse/validate it as the submitted JSON.",
        "FAILED_PROVIDER_ACCESS": "Provider access/auth/HTTP 401/403-type failure.",
        "FAILED_PROVIDER_OR_MODEL_ERROR": "Provider/runtime failure without a recoverable submitted response.",
        "FAILED_TIMEOUT": "Timeout/deadline failure.",
        "FAILED_POLICY_OR_BUDGET": "Policy or budget gate failure.",
        "FAILED_OTHER": "Failure not assigned to a narrower class.",
        "COMPLETED_INVALID_OR_UNJUDGED": "Completed artifact without a normal PASS or real evaluated mismatch.",
        "RAW_RESULT_UNREADABLE": "Raw artifact could not be parsed; preserved and not interpreted as wrong.",
        "RAW_RESULT_NOT_OBJECT": "Raw artifact is not a JSON object; preserved and not interpreted as wrong.",
    }
    for group in GROUPS:
        counts = summary["by_group"].get(group, {}).get("failure_class_counts", {})
        for key, value in counts.items():
            lines.append(f"| {group} | `{key}` | {value} | {meanings.get(key, 'See the machine-readable record.') } |")
    lines += [
        "",
        "## Per-model detail",
        "",
        "| Group | Model | Correct | Wrong (completed only) | Failed / unproven | Missing raw | Failed -> recovered correct | Failed payload wrong (not counted) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for group in GROUPS:
        for model, counts in sorted((summary["by_group"].get(group, {}).get("by_model", {}) or {}).items()):
            failed = sum(value for key, value in counts.items() if str(key).startswith("FAILED"))
            lines.append("| %s | `%s` | %s | %s | %s | %s | %s | %s |" % (
                group,
                model,
                counts.get("ANSWER_CORRECT", 0),
                counts.get("ANSWER_WRONG", 0),
                failed,
                counts.get("MISSING_RAW_RESULT", 0),
                counts.get("FAILED_RECOVERED_CORRECT", 0),
                counts.get("FAILED_WITH_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED", 0),
            ))
    lines += [
        "",
        "## Audit boundaries",
        "",
        "- The machine-readable records contain source paths and SHA-256 fingerprints, not prompts, model output, or hidden answers.",
        "- The local evaluator reads the repository's private answer key only to derive `PASS`/`MODEL_ERROR`; the answer key is not copied into this report or any committed artifact.",
        "- The raw matrix ledgers and result files remain the source of truth. This reconciliation layer is append-only and can be regenerated.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.benchmark_root.resolve()
    data_dir = args.data_dir.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    source_ledgers: list[dict[str, Any]] = []
    for group, run_dir, ledger in discover_runs(root):
        source_ledgers.append({"group": group, "run_dir": str(run_dir), "ledger_sha256": hashlib.sha256((run_dir / "matrix_completion_ledger.json").read_bytes()).hexdigest()})
        for row in ledger["rows"]:
            if isinstance(row, dict):
                records.append(audit_row(row, run_dir, data_dir))
    generated_at = datetime.now(timezone.utc).isoformat()
    summary = summarize(records)
    summary.update({
        "schema_version": 1,
        "generated_at_utc": generated_at,
        "benchmark_root": str(root),
        "data_dir": str(data_dir),
        "answer_key_read_for_local_evaluation": True,
        "raw_results_modified": False,
        "synthetic_results_created": False,
        "provider_requests_made": 0,
        "source_ledgers": source_ledgers,
    })
    (output / "failure_reconciliation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "failure_reconciliation_records.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "FAILURE_RECONCILIATION.md").write_text(markdown(summary, records, generated_at), encoding="utf-8")
    print(json.dumps({"output_dir": str(output), "row_count": len(records), "summary": summary["by_group"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
