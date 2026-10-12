#!/usr/bin/env python3
"""Audit format-failure retries without changing raw benchmark records."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from organize_benchmark_results import _cost, _error_labels, classify


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


_RECOVERY_STAGES = (
    "format_recovery",
    "format_recovery_retry2",
    "format_recovery_retry3",
    "format_recovery_retry4",
    "provider_recovery_retry1",
    "provider_recovery_retry2",
    "format_recovery_retry5",
    "provider_recovery_retry3",
    "format_recovery_retry6",
    "provider_recovery_retry4",
    "format_recovery_retry7",
    "provider_recovery_retry5",
)

# A later retry is only preferred when it is at least as useful as the
# existing candidate.  In particular, a retry that hits a 401/403/503 must
# not hide an already parseable structured response.  Ties prefer the later
# retry so that a successful repair is still selected over an earlier one.
_RECOVERY_CLASSIFICATION_RANK = {
    "answer_correct": 0,
    "answer_incorrect_structured": 1,
    "policy_violation": 2,
    "format_schema_or_missing_field": 3,
    "format_json_parse": 4,
    "transport_timeout": 5,
    "provider_error": 6,
    "model_error_or_no_answer": 7,
    "record_missing": 8,
}


def _resolution(classification: str) -> str:
    return {
        "answer_correct": "recovered_answer_correct",
        "answer_incorrect_structured": "recovered_structured_wrong_answer",
        "format_json_parse": "still_format_json_parse_failure",
        "format_schema_or_missing_field": "still_format_schema_failure",
        "transport_timeout": "recovery_transport_timeout",
        "provider_error": "recovery_provider_error",
        "policy_violation": "recovery_policy_violation",
        "model_error_or_no_answer": "recovery_model_error_or_no_answer",
        "record_missing": "recovery_record_missing",
    }.get(classification, f"recovery_{classification}")


def _recovery_index(run_dirs: set[Path]) -> tuple[dict[tuple[Path, str, str], tuple[Path, dict[str, Any]]], list[dict[str, Any]]]:
    index: dict[tuple[Path, str, str], tuple[Path, dict[str, Any]]] = {}
    invalid: list[dict[str, Any]] = []
    for run_dir in sorted(run_dirs):
        # Keep raw benchmark records untouched.  Candidate selection is
        # quality-aware: later transport/provider failures cannot replace a
        # parseable candidate, while a later candidate of equal quality wins.
        for stage_index, stage in enumerate(_RECOVERY_STAGES):
            root = run_dir / stage / "models"
            for path in sorted(root.glob("*/*.json")) if root.exists() else []:
                try:
                    result = _load(path)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    invalid.append({"run_dir": str(run_dir), "path": str(path), "error": f"{type(exc).__name__}: {exc}"})
                    continue
                task_id = str(result.get("task_id") or "")
                model_id = str(result.get("model_id") or path.parent.name)
                if not task_id:
                    invalid.append({"run_dir": str(run_dir), "path": str(path), "error": "missing_task_id"})
                    continue
                key = (run_dir, model_id, task_id)
                candidate = (path, result)
                if key not in index:
                    index[key] = candidate
                    continue
                previous_path, previous_result = index[key]
                previous_stage = previous_path.parent.parent.parent.name
                previous_stage_index = _RECOVERY_STAGES.index(previous_stage)
                candidate_key = (
                    _RECOVERY_CLASSIFICATION_RANK.get(classify(result), 99),
                    -stage_index,
                )
                previous_key = (
                    _RECOVERY_CLASSIFICATION_RANK.get(classify(previous_result), 99),
                    -previous_stage_index,
                )
                if candidate_key < previous_key:
                    index[key] = candidate
    return index, invalid


def _aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key) for key in keys)].append(row)
    output: list[dict[str, Any]] = []
    for group_key, items in sorted(groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        classifications = Counter(item["recovery_classification"] for item in items)
        resolutions = Counter(item["resolution"] for item in items)
        output.append({
            **dict(zip(keys, group_key)),
            "records": len(items),
            "recovered_answer_correct": resolutions["recovered_answer_correct"],
            "recovered_structured_wrong_answer": resolutions["recovered_structured_wrong_answer"],
            "still_format_failure": sum(value for key, value in resolutions.items() if key.startswith("still_format_")),
            "recovery_transport_timeout": resolutions["recovery_transport_timeout"],
            "recovery_provider_error": resolutions["recovery_provider_error"],
            "recovery_model_error_or_no_answer": resolutions["recovery_model_error_or_no_answer"],
            "recovery_classification_counts": dict(sorted(classifications.items())),
            "resolution_counts": dict(sorted(resolutions.items())),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--organized-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    organized = args.organized_dir.resolve()
    output = (args.output_dir or (organized / "format_failures")).resolve()
    output.mkdir(parents=True, exist_ok=True)

    selected = _load_jsonl(output / "selected_format_failures.jsonl")
    run_dirs = {Path(row["run_dir"]) for row in selected}
    recovery_index, invalid_files = _recovery_index(run_dirs)

    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for row in selected:
        key = (Path(row["run_dir"]), str(row["model_id"]), str(row["task_id"]))
        found = recovery_index.get(key)
        if not found:
            missing.append({
                "run_dir": row["run_dir"],
                "model_id": row["model_id"],
                "task_id": row["task_id"],
                "previous_selected_result_path": row["selected_result_path"],
            })
            continue
        path, result = found
        classification = classify(result)
        rows.append({
            "scope": row["scope"],
            "provider_group": row["provider_group"],
            "mode": row["mode"],
            "difficulty_level": row["difficulty_level"],
            "difficulty_label": row["difficulty_label"],
            "benchmark_run_id": row["benchmark_run_id"],
            "run_dir": row["run_dir"],
            "model_id": row["model_id"],
            "task_id": row["task_id"],
            "previous_selected_result_path": row["selected_result_path"],
            "format_recovery_result_path": str(path),
            "recovery_status": result.get("status"),
            "recovery_validation_status": (result.get("validation") or {}).get("status"),
            "recovery_protocol_valid": result.get("protocol_valid"),
            "recovery_classification": classification,
            "resolution": _resolution(classification),
            "recovery_error_labels": _error_labels(result),
            "recovery_cost_usd": _cost(result),
        })

    rows.sort(key=lambda row: (row["scope"], row["provider_group"], row["mode"], str(row["difficulty_level"]), row["model_id"], row["task_id"]))
    missing.sort(key=lambda row: (row["run_dir"], row["model_id"], row["task_id"]))
    _write_jsonl(output / "format_recovery_results.jsonl", rows)
    _write_jsonl(output / "resolved_format_failures.jsonl", rows)
    _write_jsonl(output / "format_recovery_missing.jsonl", missing)
    (output / "format_recovery_invalid_files.json").write_text(json.dumps(invalid_files, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_fields = [
        "scope", "provider_group", "mode", "difficulty_level", "model_id", "task_id",
        "recovery_classification", "resolution", "recovery_status", "recovery_validation_status",
        "recovery_protocol_valid", "recovery_cost_usd", "recovery_error_labels",
        "previous_selected_result_path", "format_recovery_result_path",
    ]
    with (output / "format_recovery_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row[field], ensure_ascii=False) if isinstance(row.get(field), list) else row.get(field, "") for field in csv_fields})

    by_model = _aggregate(rows, ("scope", "provider_group", "mode", "difficulty_level", "model_id"))
    by_resolution = _aggregate(rows, ("scope", "resolution"))
    by_scope = _aggregate(rows, ("scope",))
    for name, data in (("format_recovery_by_model.json", by_model), ("format_recovery_by_resolution.json", by_resolution), ("format_recovery_by_scope.json", by_scope)):
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    first_attempt_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery" / "models").glob("*/*.json")]
    retry2_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery_retry2" / "models").glob("*/*.json")]
    retry3_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery_retry3" / "models").glob("*/*.json")]
    retry4_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery_retry4" / "models").glob("*/*.json")]
    provider_retry1_paths = [path for run_dir in run_dirs for path in (run_dir / "provider_recovery_retry1" / "models").glob("*/*.json")]
    provider_retry2_paths = [path for run_dir in run_dirs for path in (run_dir / "provider_recovery_retry2" / "models").glob("*/*.json")]
    retry5_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery_retry5" / "models").glob("*/*.json")]
    provider_retry3_paths = [path for run_dir in run_dirs for path in (run_dir / "provider_recovery_retry3" / "models").glob("*/*.json")]
    retry6_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery_retry6" / "models").glob("*/*.json")]
    provider_retry4_paths = [path for run_dir in run_dirs for path in (run_dir / "provider_recovery_retry4" / "models").glob("*/*.json")]
    retry7_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery_retry7" / "models").glob("*/*.json")]
    provider_retry5_paths = [path for run_dir in run_dirs for path in (run_dir / "provider_recovery_retry5" / "models").glob("*/*.json")]
    # retry8 was intentionally interrupted after a deterministic policy
    # violation was confirmed.  Count its files and cost for auditability,
    # but do not use this incomplete stage as a final candidate.
    retry8_paths = [path for run_dir in run_dirs for path in (run_dir / "format_recovery_retry8" / "models").glob("*/*.json")]
    def _paths_cost(paths: list[Path]) -> float:
        total = 0.0
        for path in paths:
            try:
                total += _cost(_load(path))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
        return round(total, 8)

    first_attempt_cost = _paths_cost(first_attempt_paths)
    retry2_cost = _paths_cost(retry2_paths)
    retry3_cost = _paths_cost(retry3_paths)
    retry4_cost = _paths_cost(retry4_paths)
    provider_retry1_cost = _paths_cost(provider_retry1_paths)
    provider_retry2_cost = _paths_cost(provider_retry2_paths)
    retry5_cost = _paths_cost(retry5_paths)
    provider_retry3_cost = _paths_cost(provider_retry3_paths)
    retry6_cost = _paths_cost(retry6_paths)
    provider_retry4_cost = _paths_cost(provider_retry4_paths)
    retry7_cost = _paths_cost(retry7_paths)
    provider_retry5_cost = _paths_cost(provider_retry5_paths)
    retry8_cost = _paths_cost(retry8_paths)
    trace_error_counts: Counter[str] = Counter()
    trace_error_by_provider: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        try:
            result = _load(Path(row["format_recovery_result_path"]))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        for trace in ((result.get("metadata") or {}).get("provider_trace") or []):
            error = trace.get("error") if isinstance(trace, dict) else None
            if not isinstance(error, dict):
                continue
            label = f"{error.get('type', 'unknown')}: {error.get('message', '')}"
            trace_error_counts[label] += 1
            trace_error_by_provider[row["provider_group"]][label] += 1
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_selected_format_failures": str(output / "selected_format_failures.jsonl"),
        "selected_format_failure_count": len(selected),
        "recovery_result_count": len(rows),
        "missing_recovery_count": len(missing),
        "invalid_recovery_file_count": len(invalid_files),
        "first_attempt_result_file_count": len(first_attempt_paths),
        "retry2_result_file_count": len(retry2_paths),
        "retry3_result_file_count": len(retry3_paths),
        "retry4_result_file_count": len(retry4_paths),
        "provider_retry1_result_file_count": len(provider_retry1_paths),
        "provider_retry2_result_file_count": len(provider_retry2_paths),
        "retry5_result_file_count": len(retry5_paths),
        "provider_retry3_result_file_count": len(provider_retry3_paths),
        "retry6_result_file_count": len(retry6_paths),
        "provider_retry4_result_file_count": len(provider_retry4_paths),
        "retry7_result_file_count": len(retry7_paths),
        "provider_retry5_result_file_count": len(provider_retry5_paths),
        "retry8_result_file_count": len(retry8_paths),
        "retry8_incomplete": bool(retry8_paths),
        "recovery_classification_counts": dict(sorted(Counter(row["recovery_classification"] for row in rows).items())),
        "resolution_counts": dict(sorted(Counter(row["resolution"] for row in rows).items())),
        "final_selected_recovery_cost_usd": round(sum(float(row["recovery_cost_usd"] or 0.0) for row in rows), 8),
        "first_attempt_cost_usd": first_attempt_cost,
        "retry2_cost_usd": retry2_cost,
        "retry3_cost_usd": retry3_cost,
        "retry4_cost_usd": retry4_cost,
        "provider_retry1_cost_usd": provider_retry1_cost,
        "provider_retry2_cost_usd": provider_retry2_cost,
        "retry5_cost_usd": retry5_cost,
        "provider_retry3_cost_usd": provider_retry3_cost,
        "retry6_cost_usd": retry6_cost,
        "provider_retry4_cost_usd": provider_retry4_cost,
        "retry7_cost_usd": retry7_cost,
        "provider_retry5_cost_usd": provider_retry5_cost,
        "retry8_cost_usd": retry8_cost,
        "all_recovery_attempts_cost_usd": round(first_attempt_cost + retry2_cost + retry3_cost + retry4_cost + provider_retry1_cost + provider_retry2_cost + retry5_cost + provider_retry3_cost + retry6_cost + provider_retry4_cost + retry7_cost + provider_retry5_cost + retry8_cost, 8),
        "final_provider_trace_error_counts": dict(sorted(trace_error_counts.items())),
        "final_provider_trace_errors_by_provider": {
            key: dict(sorted(value.items())) for key, value in sorted(trace_error_by_provider.items())
        },
        "by_model": by_model,
    }
    (output / "format_recovery_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selected": len(selected),
        "recovery_results": len(rows),
        "missing": len(missing),
        "invalid": len(invalid_files),
        "resolution_counts": summary["resolution_counts"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
