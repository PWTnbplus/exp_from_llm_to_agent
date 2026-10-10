#!/usr/bin/env python3
"""Build a separate, read-only index of benchmark format failures."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _failure_type(classification: str) -> str:
    if classification == "format_json_parse":
        return "json_parse_failure"
    if classification == "format_schema_or_missing_field":
        return "schema_or_missing_field_failure"
    return "not_format_failure"


def _format_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_type = _failure_type(row["raw_classification"])
    selected_type = _failure_type(row["selected_classification"])
    if raw_type != "not_format_failure" and selected_type != "not_format_failure":
        stage = "raw_and_selected"
    elif raw_type != "not_format_failure":
        stage = "raw_only"
    else:
        stage = "after_recovery_only"
    return {
        "scope": row["scope"],
        "provider_group": row["provider_group"],
        "mode": row["mode"],
        "difficulty_level": row["difficulty_level"],
        "difficulty_label": row["difficulty_label"],
        "benchmark_run_id": row["benchmark_run_id"],
        "run_dir": row["run_dir"],
        "model_id": row["model_id"],
        "task_id": row["task_id"],
        "failure_stage": stage,
        "raw_failure_type": raw_type,
        "raw_status": row["raw_status"],
        "raw_validation_status": row["raw_validation_status"],
        "raw_protocol_valid": row["raw_protocol_valid"],
        "raw_error_labels": row["raw_error_labels"],
        "raw_result_path": row["raw_result_path"],
        "recovery_performed": row["recovery_performed"],
        "recovery_result_path": row["recovery_result_path"],
        "selected_failure_type": selected_type,
        "selected_status": row["selected_status"],
        "selected_validation_status": row["selected_validation_status"],
        "selected_protocol_valid": row["selected_protocol_valid"],
        "selected_error_labels": row["selected_error_labels"],
        "selected_result_path": row["selected_result_path"],
    }


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output = []
    for group_key, items in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        raw_types = Counter(item["raw_failure_type"] for item in items)
        selected_types = Counter(item["selected_failure_type"] for item in items)
        output.append(
            {
                **dict(zip(keys, group_key)),
                "records": len(items),
                "raw_format_failures": sum(value for key, value in raw_types.items() if key != "not_format_failure"),
                "selected_format_failures": sum(value for key, value in selected_types.items() if key != "not_format_failure"),
                "raw_json_parse_failures": raw_types["json_parse_failure"],
                "raw_schema_failures": raw_types["schema_or_missing_field_failure"],
                "selected_json_parse_failures": selected_types["json_parse_failure"],
                "selected_schema_failures": selected_types["schema_or_missing_field_failure"],
                "after_recovery_only": sum(item["failure_stage"] == "after_recovery_only" for item in items),
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--organized-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    organized = args.organized_dir.resolve()
    output = (args.output_dir or (organized / "format_failures")).resolve()
    output.mkdir(parents=True, exist_ok=True)

    index_rows = _load_jsonl(organized / "results_index.jsonl")
    format_rows = [_format_row(row) for row in index_rows if row["selected_classification"].startswith("format_") or row["raw_classification"].startswith("format_")]
    selected_rows = [row for row in format_rows if row["selected_failure_type"] != "not_format_failure"]
    raw_rows = [row for row in format_rows if row["raw_failure_type"] != "not_format_failure"]
    recovery_rows = [row for row in selected_rows if row["recovery_performed"]]

    sort_key = lambda row: (row["scope"], row["provider_group"], row["mode"], str(row["difficulty_level"]), row["model_id"], row["task_id"])
    format_rows.sort(key=sort_key)
    raw_rows.sort(key=sort_key)
    selected_rows.sort(key=sort_key)
    recovery_rows.sort(key=sort_key)

    _write_jsonl(output / "format_failures_index.jsonl", format_rows)
    _write_jsonl(output / "raw_format_failures.jsonl", raw_rows)
    _write_jsonl(output / "selected_format_failures.jsonl", selected_rows)
    _write_jsonl(output / "recovery_format_failures.jsonl", recovery_rows)

    csv_fields = [
        "scope", "provider_group", "mode", "difficulty_level", "model_id", "task_id", "failure_stage",
        "raw_failure_type", "selected_failure_type", "raw_validation_status", "selected_validation_status",
        "raw_protocol_valid", "selected_protocol_valid", "recovery_performed", "raw_error_labels",
        "selected_error_labels", "raw_result_path", "recovery_result_path", "selected_result_path",
    ]
    with (output / "format_failures.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in format_rows:
            writer.writerow({field: json.dumps(row[field], ensure_ascii=False) if isinstance(row[field], list) else row.get(field, "") for field in csv_fields})

    by_model = _aggregate(format_rows, ("scope", "provider_group", "mode", "difficulty_level", "model_id"))
    by_type = _aggregate(format_rows, ("scope", "raw_failure_type", "selected_failure_type"))
    by_scope = _aggregate(format_rows, ("scope",))
    for name, data in (("by_model.json", by_model), ("by_failure_type.json", by_type), ("by_scope.json", by_scope)):
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_index": str(organized / "results_index.jsonl"),
        "raw_format_failure_count": len(raw_rows),
        "selected_format_failure_count": len(selected_rows),
        "format_failure_index_count": len(format_rows),
        "recovery_format_failure_count": len(recovery_rows),
        "failure_stage_counts": dict(Counter(row["failure_stage"] for row in format_rows)),
        "raw_failure_type_counts": dict(Counter(row["raw_failure_type"] for row in format_rows)),
        "selected_failure_type_counts": dict(Counter(row["selected_failure_type"] for row in format_rows)),
        "by_model": by_model,
    }
    (output / "format_failure_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme = """# Format-failure organization

This directory is a separate analysis view. It contains indexes and aggregate tables only; it does not move, overwrite, or rewrite any raw benchmark result JSON.

- `raw_format_failures.jsonl`: records whose original attempt failed JSON parsing or the required response schema.
- `selected_format_failures.jsonl`: records whose selected attempt (a retry when available, otherwise the original) still failed formatting.
- `recovery_format_failures.jsonl`: selected format failures that came from a retry attempt.
- `format_failures.csv`: Excel-friendly combined index with raw/retry paths.

`json_parse_failure` means the response could not be decoded as JSON. `schema_or_missing_field_failure` means a response existed but did not satisfy the required response fields. A structured response with wrong scientific values is intentionally not included here; it is an answer error, not a format error.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({
        "output_dir": str(output),
        "raw_format_failures": len(raw_rows),
        "selected_format_failures": len(selected_rows),
        "recovery_format_failures": len(recovery_rows),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
