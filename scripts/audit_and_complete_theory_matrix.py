#!/usr/bin/env python3
"""Audit and complete the *metadata* layer of a G2/G3 theory matrix.

The raw matrix is intentionally immutable here.  This command verifies that
the manifest, result files, and trace files can actually be read, probes
whether the run/model directories can accept a temporary file, and writes a
complete task-by-model ledger.  Missing experiments remain explicit missing
rows; no result, answer, success, or failure is invented.

The script never loads ``answers.json`` or any private answer key.  Its only
benchmark input is the public task list used to build the registered
denominator.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid
from typing import Any


REPORT_NAME = "matrix_io_integrity_report.json"
LEDGER_NAME = "matrix_completion_ledger.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def read_utf8(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_bytes().decode("utf-8"), None
    except (OSError, UnicodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def parse_json_file(path: Path) -> tuple[Any | None, str | None]:
    text, error = read_utf8(path)
    if error is not None:
        return None, error
    try:
        return json.loads(text or ""), None
    except json.JSONDecodeError as exc:
        return None, f"JSONDecodeError: {exc.msg} at line {exc.lineno}, column {exc.colno}"


def probe_directory(directory: Path) -> dict[str, Any]:
    """Probe create/write/read/delete without leaving an artifact."""
    result: dict[str, Any] = {"exists": directory.is_dir(), "writable": False, "error": None}
    if not result["exists"]:
        result["error"] = "directory_missing"
        return result
    probe: Path | None = None
    try:
        fd, raw_path = tempfile.mkstemp(prefix=".__matrix_io_probe_", suffix=".tmp", dir=directory)
        probe = Path(raw_path)
        with os.fdopen(fd, "wb") as handle:
            handle.write(b"matrix-io-probe\n")
            handle.flush()
            os.fsync(handle.fileno())
        if probe.read_bytes() != b"matrix-io-probe\n":
            raise OSError("probe readback mismatch")
        result["writable"] = True
    except (OSError, UnicodeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if probe is not None:
            try:
                probe.unlink()
            except OSError as exc:
                result["cleanup_error"] = f"{type(exc).__name__}: {exc}"
    return result


def safe_trace_path(model_dir: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "trace_path_missing_or_not_string"
    root = model_dir.resolve()
    candidate = (model_dir / Path(value)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, "trace_path_escapes_model_directory"
    return candidate, None


def inspect_trace(path: Path) -> dict[str, Any]:
    text, error = read_utf8(path)
    result: dict[str, Any] = {
        "exists": path.is_file(),
        "readable": error is None,
        "utf8": error is None,
        "jsonl_lines": 0,
        "invalid_jsonl_lines": [],
        "error": error,
    }
    if error is not None or text is None:
        return result
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        result["jsonl_lines"] += 1
        try:
            json.loads(line)
        except json.JSONDecodeError:
            result["invalid_jsonl_lines"].append(line_number)
    result["jsonl_valid"] = not result["invalid_jsonl_lines"]
    return result


def model_ids_from_manifest(manifest: dict[str, Any]) -> list[str]:
    models = manifest.get("models") or []
    values: list[str] = []
    for row in models:
        if isinstance(row, dict):
            values.append(str(row.get("model_id")))
        else:
            values.append(str(row))
    return values


def expected_task_ids(data_dir: Path, manifest: dict[str, Any]) -> list[str]:
    public = load_json(data_dir / "public_tasks.json")
    limit = int(manifest.get("tasks_per_model", len(public)))
    values = [str(row["task_id"]) for row in public[:limit] if isinstance(row, dict) and "task_id" in row]
    if len(values) != len(set(values)):
        raise ValueError("public task list contains duplicate task IDs")
    return values


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str) and bool(value.strip())
    if expected == "string_or_null":
        return value is None or (isinstance(value, str) and bool(value.strip()))
    if expected == "bool":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "list":
        return isinstance(value, list)
    if expected == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return _is_number(value)
    if expected == "any":
        return True
    raise ValueError(f"unsupported field type: {expected}")


def derive_task_id_from_filename(path: Path, mode: str, expected_task_ids: list[str]) -> str | None:
    """Return a task ID only when the registered filename encoding is unique."""
    stem = path.stem
    prefix = f"{mode}__"
    matches = [
        task_id
        for task_id in expected_task_ids
        if stem.startswith(f"{prefix}{task_id.replace(':', '__')}__")
    ]
    return matches[0] if len(matches) == 1 else None


def audit_result_fields(
    result: dict[str, Any],
    *,
    mode: str,
    model_id: str,
    expected_task_id: str | None,
) -> dict[str, Any]:
    """Check the runner result contract without reading any answer key."""
    required: dict[str, str] = {
        "task_id": "string",
        "runner": "string",
        "mode": "string",
        "group": "string",
        "model_id": "string",
        "status": "string",
        "protocol_valid": "bool",
        "evaluator_valid": "bool",
        "mock": "bool",
        "answer": "any",
        "task": "object",
        "validation": "object",
        "run_id": "string",
        "trace_path": "string_or_null",
        "metadata": "object",
    }
    validation_fields = {
        "status": "string",
        "task_id": "string",
        "answer_correct": "bool",
        "errors": "list",
    }
    metadata_fields = {
        "started_at": "string",
        "provider_calls": "int",
        "provider_trace": "list",
        "policy": "object",
        "budget": "object",
    }
    budget_fields = {"input_tokens": "number", "output_tokens": "number", "cost_usd": "number"}
    issues: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []

    def check(container: dict[str, Any], field: str, expected: str, prefix: str) -> None:
        if field not in container:
            issues.append({"field": f"{prefix}{field}", "code": "MISSING", "expected": expected})
        elif not _type_ok(container[field], expected):
            issues.append(
                {
                    "field": f"{prefix}{field}",
                    "code": "TYPE_INVALID",
                    "expected": expected,
                    "actual": type(container[field]).__name__,
                }
            )

    for field, expected in required.items():
        check(result, field, expected, "")

    validation = result.get("validation")
    if isinstance(validation, dict):
        for field, expected in validation_fields.items():
            check(validation, field, expected, "validation.")
    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        for field, expected in metadata_fields.items():
            check(metadata, field, expected, "metadata.")
        budget = metadata.get("budget")
        if isinstance(budget, dict):
            used = budget.get("used")
            if not isinstance(used, dict):
                issues.append({"field": "metadata.budget.used", "code": "MISSING_OR_INVALID", "expected": "object"})
            else:
                for field, expected in budget_fields.items():
                    check(used, field, expected, "metadata.budget.used.")

    def add_repair(field: str, value: Any, source: str) -> None:
        repairs.append({"field": field, "derived_value": value, "source": source, "raw_unchanged": True})

    # These values are uniquely fixed by the registered run context.  They are
    # reported as a repair plan, never inserted into the raw result.
    if "task_id" not in result and expected_task_id is not None:
        add_repair("task_id", expected_task_id, "registered_filename")
    if "runner" not in result:
        add_repair("runner", mode, "manifest.mode")
    if "mode" not in result:
        add_repair("mode", mode, "manifest.mode")
    if "group" not in result:
        add_repair("group", mode, "manifest.mode")
    if "model_id" not in result:
        add_repair("model_id", model_id, "manifest.model_directory")
    if isinstance(validation, dict) and "task_id" not in validation and expected_task_id is not None:
        add_repair("validation.task_id", expected_task_id, "registered_filename")

    issue_codes = Counter(issue["code"] for issue in issues)
    return {
        "complete": not issues,
        "issues": issues,
        "issue_counts": [{"key": key, "count": issue_codes[key]} for key in sorted(issue_codes)],
        "repairable_fields": repairs,
        "repairable_field_count": len(repairs),
    }


def summary_exit_codes(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "parallel_launcher_summary.json"
    payload, error = parse_json_file(path)
    if error is not None or not isinstance(payload, dict):
        return {"readable": False, "error": error or "summary_is_not_an_object", "models": {}}
    rows = payload.get("results") or []
    values: dict[str, Any] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("model_id") is not None:
            values[str(row["model_id"])] = {"exit_code": row.get("exit_code"), "status": row.get("status")}
    return {
        "readable": True,
        "all_processes_exit_zero": payload.get("all_processes_exit_zero"),
        "finished_at_utc": payload.get("finished_at_utc"),
        "models": values,
    }


def inspect_run(run_dir: Path, data_dir: Path, write_derived: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, manifest_error = parse_json_file(run_dir / "run_manifest.json")
    if manifest_error is not None or not isinstance(manifest, dict):
        raise RuntimeError(f"cannot read run manifest: {manifest_error or 'not an object'}")
    mode = str(manifest.get("mode"))
    if mode not in {"G2", "G3"}:
        raise ValueError(f"unsupported matrix mode: {mode}")
    task_ids = expected_task_ids(data_dir, manifest)
    expected_set = set(task_ids)
    model_ids = model_ids_from_manifest(manifest)
    if len(model_ids) != len(set(model_ids)):
        raise ValueError("run manifest contains duplicate model IDs")

    run_probe = probe_directory(run_dir)
    exits = summary_exit_codes(run_dir)
    model_reports: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    for model_id in model_ids:
        model_dir = run_dir / "models" / model_id
        model_probe = probe_directory(model_dir)
        result_paths = sorted(model_dir.glob(f"{mode}__*.json")) if model_dir.is_dir() else []
        parsed_by_task: dict[str, list[dict[str, Any]]] = {}
        malformed: list[dict[str, Any]] = []
        result_read_errors: list[dict[str, Any]] = []
        trace_errors: list[dict[str, Any]] = []
        wrong_mode: list[str] = []
        wrong_group: list[str] = []
        field_issue_counts: Counter[str] = Counter()
        field_issue_files: list[dict[str, Any]] = []
        field_repair_rows: list[dict[str, Any]] = []
        credential_hits = 0
        for path in result_paths:
            raw, read_error = read_utf8(path)
            if read_error is not None or raw is None:
                result_read_errors.append({"file": path.name, "error": read_error})
                continue
            try:
                result = json.loads(raw)
            except json.JSONDecodeError as exc:
                malformed.append({"file": path.name, "error": f"line {exc.lineno}, column {exc.colno}"})
                continue
            if not isinstance(result, dict):
                malformed.append({"file": path.name, "error": "result_is_not_an_object"})
                continue
            serialized = json.dumps(result, ensure_ascii=False)
            credential_hits += serialized.lower().count("sk-")
            raw_task_id = result.get("task_id")
            derived_task_id = derive_task_id_from_filename(path, mode, task_ids)
            task_id = (
                str(raw_task_id)
                if isinstance(raw_task_id, str) and raw_task_id.strip()
                else derived_task_id or f"__UNIDENTIFIED__{path.name}"
            )
            field_audit = audit_result_fields(
                result,
                mode=mode,
                model_id=model_id,
                expected_task_id=derived_task_id,
            )
            for issue in field_audit["issues"]:
                field_issue_counts[issue["code"]] += 1
            if field_audit["issues"]:
                field_issue_files.append(
                    {
                        "file": path.name,
                        "task_id": derived_task_id or raw_task_id,
                        "issues": field_audit["issues"],
                    }
                )
            for repair in field_audit["repairable_fields"]:
                field_repair_rows.append(
                    {
                        "model_id": model_id,
                        "task_id": derived_task_id or raw_task_id,
                        "raw_result_path": str(path),
                        **repair,
                    }
                )
            entry = {
                "path": str(path),
                "name": path.name,
                "result": result,
                "field_audit": field_audit,
                "derived_task_id": derived_task_id,
            }
            parsed_by_task.setdefault(task_id, []).append(entry)
            if result.get("mode") != mode:
                wrong_mode.append(path.name)
            if result.get("group") != mode:
                wrong_group.append(path.name)
            trace_path, trace_path_error = safe_trace_path(model_dir, result.get("trace_path"))
            if trace_path_error is not None or trace_path is None:
                trace_errors.append({"file": path.name, "error": trace_path_error})
            elif not trace_path.is_file():
                trace_errors.append({"file": path.name, "error": "trace_file_missing", "trace_path": str(trace_path)})
            else:
                trace_report = inspect_trace(trace_path)
                if not trace_report.get("readable") or not trace_report.get("jsonl_valid", True):
                    trace_errors.append({"file": path.name, "trace_path": str(trace_path), "error": trace_report})
        missing = sorted(expected_set - set(parsed_by_task))
        unexpected = sorted(set(parsed_by_task) - expected_set)
        duplicates = {key: len(value) for key, value in parsed_by_task.items() if len(value) > 1}
        exit_info = exits.get("models", {}).get(model_id, {})
        model_reports.append(
            {
                "model_id": model_id,
                "directory_probe": model_probe,
                "result_file_count": len(result_paths),
                "result_read_errors": result_read_errors,
                "malformed_result_files": malformed,
                "trace_read_errors": trace_errors,
                "wrong_mode_files": wrong_mode,
                "wrong_group_files": wrong_group,
                "credential_marker_hits": credential_hits,
                "field_issue_counts": [
                    {"key": key, "count": field_issue_counts[key]}
                    for key in sorted(field_issue_counts)
                ],
                "field_issue_file_count": len(field_issue_files),
                "field_issue_files": field_issue_files,
                "field_repair_count": len(field_repair_rows),
                "field_schema_complete": not field_issue_files,
                "task_ids_recorded": len(set(parsed_by_task) & expected_set),
                "missing_task_ids": missing,
                "unexpected_task_ids": unexpected,
                "duplicate_task_ids": duplicates,
                "launcher": exit_info,
                "raw_io_complete": (
                    len(result_paths) == len(expected_set)
                    and not result_read_errors
                    and not malformed
                    and not missing
                    and not unexpected
                    and not duplicates
                    and not trace_errors
                    and not wrong_mode
                    and not wrong_group
                    and not field_issue_files
                ),
            }
        )
        for task_id in task_ids:
            candidates = parsed_by_task.get(task_id, [])
            if len(candidates) == 0:
                state = "MISSING_RAW_RESULT"
                row: dict[str, Any] = {
                    "model_id": model_id,
                    "task_id": task_id,
                    "state": state,
                    "raw_result_path": None,
                    "raw_status": None,
                    "validation_status": None,
                    "reason": "no_result_file_with_this_task_id",
                }
            elif len(candidates) > 1:
                chosen = candidates[0]
                result = chosen["result"]
                row = {
                    "model_id": model_id,
                    "task_id": task_id,
                    "state": "DUPLICATE_RAW_RESULTS",
                    "raw_result_path": chosen["path"],
                    "raw_status": result.get("status"),
                    "validation_status": (result.get("validation") or {}).get("status"),
                    "reason": "more_than_one_raw_result_for_registered_task",
                    "duplicate_paths": [candidate["path"] for candidate in candidates],
                }
            else:
                result = candidates[0]["result"]
                raw_status = result.get("status")
                field_audit = candidates[0]["field_audit"]
                row = {
                    "model_id": model_id,
                    "task_id": task_id,
                    "state": (
                        "SCHEMA_INCOMPLETE"
                        if not field_audit["complete"]
                        else "RECORDED_FAILURE" if raw_status != "COMPLETED" else "RECORDED_RESULT"
                    ),
                    "raw_result_path": candidates[0]["path"],
                    "raw_status": raw_status,
                    "validation_status": (result.get("validation") or {}).get("status"),
                    "reason": "raw_result_preserved",
                }
                if not field_audit["complete"]:
                    row["field_issues"] = field_audit["issues"]
                    row["repairable_fields"] = field_audit["repairable_fields"]
            ledger_rows.append(row)

    counts = Counter(row["state"] for row in ledger_rows)
    report = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "run_dir": str(run_dir),
        "mode": mode,
        "group": manifest.get("group"),
        "answer_key_read": False,
        "raw_results_modified": False,
        "synthetic_results_created": False,
        "run_directory_probe": run_probe,
        "launcher_summary": exits,
        "expected_tasks_per_model": len(task_ids),
        "registered_models": len(model_ids),
        "expected_task_model_rows": len(task_ids) * len(model_ids),
        "completion_state_counts": dict(counts),
        "models": model_reports,
        "field_repair_ledger": field_repair_rows,
        "field_repair_ledger_complete": all(
            row.get("raw_unchanged") is True for row in field_repair_rows
        ),
        "field_schema_complete": all(row["field_schema_complete"] for row in model_reports),
        "all_model_directories_writable": all(row["directory_probe"].get("writable") for row in model_reports),
        "all_model_raw_io_complete": all(row["raw_io_complete"] for row in model_reports),
        "derived_completion_ledger_complete": len(ledger_rows) == len(task_ids) * len(model_ids),
        "repair_scope": [
            "validated UTF-8 and JSON readability",
            "validated trace path containment and JSONL readability",
            "validated the runner result, validation, metadata, and budget field contract",
            "recorded only context-derived field repair plans; no raw result was rewritten",
            "probed run/model directory writeability with temporary files",
            "wrote a complete denominator ledger without fabricating results",
        ],
    }
    ledger = {
        "schema_version": 1,
        "generated_at_utc": report["generated_at_utc"],
        "run_dir": str(run_dir),
        "mode": mode,
        "group": manifest.get("group"),
        "answer_key_read": False,
        "raw_results_modified": False,
        "synthetic_results_created": False,
        "expected_task_ids": task_ids,
        "model_ids": model_ids,
        "rows": ledger_rows,
        "field_repair_ledger": field_repair_rows,
        "field_repair_ledger_complete": all(
            row.get("raw_unchanged") is True for row in field_repair_rows
        ),
        "state_definitions": {
            "RECORDED_RESULT": "A readable raw result with status COMPLETED.",
            "RECORDED_FAILURE": "A readable raw result whose recorded status is not COMPLETED.",
            "SCHEMA_INCOMPLETE": "A readable raw result whose required result/validation/metadata field contract is incomplete or has invalid types.",
            "MISSING_RAW_RESULT": "No raw result was recorded for the registered task/model pair.",
            "DUPLICATE_RAW_RESULTS": "More than one raw result was recorded for the registered task/model pair.",
        },
    }
    if write_derived:
        atomic_write_json(run_dir / REPORT_NAME, report)
        atomic_write_json(run_dir / LEDGER_NAME, ledger)
        report["derived_artifacts_written"] = [REPORT_NAME, LEDGER_NAME]
    else:
        report["derived_artifacts_written"] = []
    return report, ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", action="append", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--write-derived", action="store_true")
    args = parser.parse_args()
    reports: list[dict[str, Any]] = []
    failures = 0
    for raw_run_dir in args.run_dir:
        try:
            report, _ = inspect_run(raw_run_dir.resolve(), args.data_dir.resolve(), args.write_derived)
            reports.append(report)
            if not report.get("all_model_raw_io_complete"):
                failures += 1
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            reports.append({"run_dir": str(raw_run_dir.resolve()), "error": f"{type(exc).__name__}: {exc}"})
            failures += 1
    print(json.dumps({"runs": reports}, ensure_ascii=False, indent=2))
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
