#!/usr/bin/env python3
"""Create an analysis index without copying or mutating raw benchmark data.

The output is a compact, answer-focused view.  Raw result JSON files remain in
their original run directories; the organized files contain paths, status
labels, validation labels, and aggregate counts only.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable


TIMEOUT_WORDS = ("timeout", "timed out", "time out", "deadline exceeded", "deadline reached")
PROVIDER_ERROR_TYPES = {
    "httperror",
    "connectionerror",
    "authenticationerror",
    "badrequesterror",
    "ratelimiterror",
    "serviceunavailableerror",
    "internalservererror",
    "apierror",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _text(value: Any) -> str:
    return str(value or "")


def _trace_errors(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item.get("error") or {}
        for item in ((result.get("metadata") or {}).get("provider_trace") or [])
        if isinstance(item, dict) and item.get("error")
    ]


def _error_labels(result: dict[str, Any]) -> list[str]:
    labels = set()
    for error in _trace_errors(result):
        if error.get("type"):
            labels.add(_text(error["type"]))
    for error in ((result.get("validation") or {}).get("errors") or []):
        labels.add(_text(error))
    answer = result.get("answer")
    if isinstance(answer, dict) and answer.get("error"):
        message = _text(answer.get("error"))
        if "JSONDecodeError" in message:
            labels.add("JSONDecodeError")
        elif "PolicyViolation" in message:
            labels.add("PolicyViolation")
    return sorted(labels)


def _is_timeout(result: dict[str, Any]) -> bool:
    for error in _trace_errors(result):
        if _text(error.get("type")).lower() in {"timeouterror", "timeout", "apitimeouterror"}:
            return True
        if any(word in _text(error.get("message")).lower() for word in TIMEOUT_WORDS):
            return True
    answer = result.get("answer")
    return isinstance(answer, dict) and any(
        word in _text(answer.get("error")).lower() for word in TIMEOUT_WORDS
    )


def _has_provider_error(result: dict[str, Any]) -> bool:
    for error in _trace_errors(result):
        if _text(error.get("type")).lower() in PROVIDER_ERROR_TYPES:
            return True
    answer = result.get("answer")
    message = _text(answer.get("error") if isinstance(answer, dict) else "").lower()
    return any(token in message for token in ("http", "provider request failed", "api error", "status code"))


def classify(result: dict[str, Any] | None) -> str:
    """Classify what happened, keeping transport, format, and answer errors apart."""
    if not result:
        return "record_missing"
    if _is_timeout(result):
        return "transport_timeout"
    errors = [_text(item) for item in ((result.get("validation") or {}).get("errors") or [])]
    answer = result.get("answer")
    answer_error = _text(answer.get("error") if isinstance(answer, dict) else "")
    if "PolicyViolation" in errors or "PolicyViolation" in answer_error:
        return "policy_violation"
    if _has_provider_error(result):
        return "provider_error"
    if "JSONDecodeError" in errors or "JSONDecodeError" in answer_error:
        return "format_json_parse"
    validation = result.get("validation") or {}
    if validation.get("status") == "PASS" and bool(validation.get("answer_correct")):
        return "answer_correct"
    if result.get("protocol_valid") is True and any(
        error.startswith("validation mismatch at ") for error in errors
    ):
        return "answer_incorrect_structured"
    if result.get("protocol_valid") is False or answer_error:
        return "format_schema_or_missing_field"
    if result.get("status") == "COMPLETED" and result.get("protocol_valid") is True:
        return "answer_incorrect_structured"
    return "model_error_or_no_answer"


def _cost(result: dict[str, Any] | None) -> float:
    if not result:
        return 0.0
    used = (((result.get("metadata") or {}).get("budget") or {}).get("used") or {})
    try:
        return float(used.get("cost_usd", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _run_metadata(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    run_dir = manifest_path.parent
    provider_group = _text(manifest.get("provider_group")) or run_dir.parts[-3].removesuffix("_without_lim")
    mode = _text(manifest.get("mode")) or _text(manifest.get("group"))
    return {
        "run_dir": run_dir,
        "scope": "unlimited" if any("_without_lim" in part for part in run_dir.parts) else "limited_or_legacy",
        "provider_group": provider_group,
        "mode": mode,
        "difficulty_level": manifest.get("difficulty_level"),
        "difficulty_label": manifest.get("difficulty_label"),
        "run_id": _text(manifest.get("run_id")),
        "manifest_path": manifest_path,
    }


def _result_paths(run_dir: Path) -> Iterable[Path]:
    return sorted((run_dir / "models").glob("*/*.json"))


def _recovery_index(run_dir: Path) -> dict[tuple[str, str], tuple[Path, dict[str, Any]]]:
    index: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for path in sorted((run_dir / "timeout_recovery" / "models").glob("*/*.json")):
        try:
            result = _load(path)
        except (OSError, json.JSONDecodeError):
            continue
        task_id = _text(result.get("task_id"))
        model_id = _text(result.get("model_id")) or path.parent.name
        if task_id:
            index[(model_id, task_id)] = (path, result)
    return index


def _row(run: dict[str, Any], raw_path: Path, raw: dict[str, Any], recovery: tuple[Path, dict[str, Any]] | None) -> dict[str, Any]:
    raw_model = _text(raw.get("model_id")) or raw_path.parent.name
    task_id = _text(raw.get("task_id"))
    raw_class = classify(raw)
    if recovery:
        recovery_path, recovery_result = recovery
        selected_path, selected = recovery_path, recovery_result
        selected_source = "recovery"
        recovery_class = classify(recovery_result)
    else:
        selected_path, selected = raw_path, raw
        selected_source = "raw"
        recovery_class = "not_retried"
    selected_class = classify(selected)
    return {
        "scope": run["scope"],
        "provider_group": run["provider_group"],
        "mode": run["mode"],
        "difficulty_level": run["difficulty_level"],
        "difficulty_label": run["difficulty_label"],
        "benchmark_run_id": run["run_id"],
        "run_dir": str(run["run_dir"]),
        "model_id": raw_model,
        "task_id": task_id,
        "raw_result_path": str(raw_path),
        "raw_status": raw.get("status"),
        "raw_validation_status": (raw.get("validation") or {}).get("status"),
        "raw_protocol_valid": raw.get("protocol_valid"),
        "raw_classification": raw_class,
        "raw_error_labels": _error_labels(raw),
        "recovery_performed": bool(recovery),
        "recovery_result_path": str(recovery[0]) if recovery else "",
        "recovery_classification": recovery_class,
        "selected_source": selected_source,
        "selected_result_path": str(selected_path),
        "selected_status": selected.get("status"),
        "selected_validation_status": (selected.get("validation") or {}).get("status"),
        "selected_protocol_valid": selected.get("protocol_valid"),
        "selected_classification": selected_class,
        "selected_error_labels": _error_labels(selected),
        "selected_answer_available": selected_class in {"answer_correct", "answer_incorrect_structured"},
        "selected_answer_correct": selected_class == "answer_correct",
        "raw_cost_usd": _cost(raw),
        "selected_cost_usd": _cost(selected),
    }


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key) for key in keys)].append(row)
    output = []
    for group_key, items in sorted(groups.items(), key=lambda item: tuple(_text(x) for x in item[0])):
        raw_counts = Counter(item["raw_classification"] for item in items)
        selected_counts = Counter(item["selected_classification"] for item in items)
        output.append(
            {
                **dict(zip(keys, group_key)),
                "records": len(items),
                "recovery_performed": sum(item["recovery_performed"] for item in items),
                "selected_answer_available": sum(item["selected_answer_available"] for item in items),
                "selected_answer_correct": sum(item["selected_answer_correct"] for item in items),
                "selected_format_failures": sum(item["selected_classification"].startswith("format_") for item in items),
                "raw_transport_timeouts": raw_counts["transport_timeout"],
                "selected_transport_timeouts": selected_counts["transport_timeout"],
                "raw_format_failures": sum(value for key, value in raw_counts.items() if key.startswith("format_")),
                "selected_classification_counts": dict(sorted(selected_counts.items())),
                "raw_classification_counts": dict(sorted(raw_counts.items())),
                "selected_cost_usd": round(sum(item["selected_cost_usd"] for item in items), 8),
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = args.benchmark_root.resolve()
    output = (args.output_dir or (root / "organized")).resolve()
    output.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    run_count = 0
    recovery_count = 0
    orphan_recovery = 0
    for manifest_path in sorted(root.rglob("run_manifest.json")):
        manifest = _load(manifest_path)
        run = _run_metadata(manifest_path, manifest)
        recovery = _recovery_index(run["run_dir"])
        recovery_count += len(recovery)
        matched: set[tuple[str, str]] = set()
        for raw_path in _result_paths(run["run_dir"]):
            try:
                raw = _load(raw_path)
            except (OSError, json.JSONDecodeError):
                continue
            model_id = _text(raw.get("model_id")) or raw_path.parent.name
            task_id = _text(raw.get("task_id"))
            key = (model_id, task_id)
            if key in recovery:
                matched.add(key)
            rows.append(_row(run, raw_path, raw, recovery.get(key)))
        orphan_recovery += len(set(recovery) - matched)
        run_count += 1

    rows.sort(key=lambda row: (row["scope"], row["provider_group"], row["mode"], _text(row["difficulty_level"]), row["model_id"], row["task_id"], row["raw_result_path"]))
    _write_jsonl(output / "results_index.jsonl", rows)
    _write_jsonl(output / "format_failures.jsonl", (row for row in rows if row["selected_classification"].startswith("format_")))
    _write_jsonl(output / "answer_results.jsonl", (row for row in rows if row["selected_answer_available"]))

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "organization_version": 1,
        "source_benchmark_root": str(root),
        "raw_run_count": run_count,
        "raw_record_count": len(rows),
        "recovery_result_count": recovery_count,
        "matched_recovery_count": sum(row["recovery_performed"] for row in rows),
        "orphan_recovery_count": orphan_recovery,
        "raw_classification_counts": dict(sorted(Counter(row["raw_classification"] for row in rows).items())),
        "selected_classification_counts": dict(sorted(Counter(row["selected_classification"] for row in rows).items())),
        "selected_answer_available_count": sum(row["selected_answer_available"] for row in rows),
        "selected_answer_correct_count": sum(row["selected_answer_correct"] for row in rows),
        "selected_format_failure_count": sum(row["selected_classification"].startswith("format_") for row in rows),
        "aggregates": {
            "by_provider_mode_level": _aggregate(rows, ("scope", "provider_group", "mode", "difficulty_level")),
            "by_model": _aggregate(rows, ("scope", "provider_group", "mode", "difficulty_level", "model_id")),
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    identities = [(row["run_dir"], row["model_id"], row["task_id"], row["raw_result_path"]) for row in rows]
    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_record_count": len(rows),
        "duplicate_index_identity_count": len(identities) - len(set(identities)),
        "missing_raw_path_count": sum(not Path(row["raw_result_path"]).exists() for row in rows),
        "missing_selected_path_count": sum(not Path(row["selected_result_path"]).exists() for row in rows),
        "raw_timeout_without_recovery_count": sum(row["raw_classification"] == "transport_timeout" and not row["recovery_performed"] for row in rows),
        "recovery_records": recovery_count,
        "matched_recovery_count": sum(row["recovery_performed"] for row in rows),
        "orphan_recovery_count": orphan_recovery,
        "recovery_summary_count": sum(1 for _ in root.rglob("timeout_recovery_summary.json")),
    }
    (output / "organization_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "by_model.json").write_text(json.dumps(summary["aggregates"]["by_model"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fieldnames = [
        "scope", "provider_group", "mode", "difficulty_level", "model_id", "records", "recovery_performed",
        "selected_answer_available", "selected_answer_correct", "selected_format_failures",
        "raw_transport_timeouts", "selected_transport_timeouts", "raw_format_failures", "selected_cost_usd",
        "raw_classification_counts", "selected_classification_counts",
    ]
    with (output / "by_model.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in summary["aggregates"]["by_model"]:
            writer.writerow({field: json.dumps(item[field], ensure_ascii=False) if isinstance(item[field], dict) else item.get(field, "") for field in fieldnames})

    readme = """# Organized benchmark view

This directory is an analysis index; raw result JSON files remain in their original run directories.

Classification precedence:

1. `transport_timeout`: provider trace or answer error indicates a transport timeout.
2. `provider_error`: upstream HTTP/API/connection failure.
3. `policy_violation`: runner policy blocked the call.
4. `format_json_parse`: the model response could not be parsed as JSON.
5. `format_schema_or_missing_field`: a response was present but did not satisfy the required response schema.
6. `answer_correct`: structured response passed validation and matches the answer key.
7. `answer_incorrect_structured`: structured response was parsed, but one or more answer values mismatched.

`raw_*` fields describe the original attempt. `selected_*` prefers the recovery attempt when one exists; otherwise it uses the original. This keeps transport recovery visible without overwriting the raw benchmark.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({
        "output_dir": str(output),
        "runs": run_count,
        "raw_records": len(rows),
        "recovery_records": recovery_count,
        "matched_recovery": sum(row["recovery_performed"] for row in rows),
        "orphan_recovery": orphan_recovery,
        "selected_answer_available": sum(row["selected_answer_available"] for row in rows),
        "selected_format_failures": sum(row["selected_classification"].startswith("format_") for row in rows),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
