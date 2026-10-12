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
            task_id = str(result.get("task_id"))
            entry = {"path": str(path), "name": path.name, "result": result}
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
                row = {
                    "model_id": model_id,
                    "task_id": task_id,
                    "state": "RECORDED_FAILURE" if raw_status != "COMPLETED" else "RECORDED_RESULT",
                    "raw_result_path": candidates[0]["path"],
                    "raw_status": raw_status,
                    "validation_status": (result.get("validation") or {}).get("status"),
                    "reason": "raw_result_preserved",
                }
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
        "all_model_directories_writable": all(row["directory_probe"].get("writable") for row in model_reports),
        "all_model_raw_io_complete": all(row["raw_io_complete"] for row in model_reports),
        "derived_completion_ledger_complete": len(ledger_rows) == len(task_ids) * len(model_ids),
        "repair_scope": [
            "validated UTF-8 and JSON readability",
            "validated trace path containment and JSONL readability",
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
        "state_definitions": {
            "RECORDED_RESULT": "A readable raw result with status COMPLETED.",
            "RECORDED_FAILURE": "A readable raw result whose recorded status is not COMPLETED.",
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
