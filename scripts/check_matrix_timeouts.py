#!/usr/bin/env python3
"""Inventory missing tasks and timeout-like failures without reading answer keys."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


TIMEOUT_RE = re.compile(
    r"\b(?:timeout|timed[ -]?out|time[ -]?out|deadline(?: exceeded| reached)?|"
    r"read timed out|connect timed out|request timed out|超时|响应超时)\b",
    re.IGNORECASE,
)


def load_manifest(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))


def text_hits(path: Path) -> int:
    try:
        return len(TIMEOUT_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return 0


def inspect_run(run_dir: Path, write: bool = True) -> dict[str, Any]:
    manifest = load_manifest(run_dir)
    models = [str(model) for model in manifest.get("models", [])]
    expected = int(manifest.get("tasks_expected_per_model", 100))
    model_rows: list[dict[str, Any]] = []
    all_timeout_files: list[dict[str, Any]] = []
    for model in models:
        model_dir = run_dir / "models" / model
        paths = sorted(model_dir.glob("*.json")) if model_dir.exists() else []
        task_ids: list[str] = []
        status_counts: Counter[str] = Counter()
        model_timeout_hits = 0
        timeout_task_ids: set[str] = set()
        for path in paths:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            task_id = payload.get("task_id")
            if task_id is not None:
                task_ids.append(str(task_id))
            status_counts[str(payload.get("status", "<missing>"))] += 1
            raw = json.dumps(payload, ensure_ascii=False)
            hits = len(TIMEOUT_RE.findall(raw))
            if hits:
                model_timeout_hits += hits
                if task_id is not None:
                    timeout_task_ids.add(str(task_id))
        for path in sorted(model_dir.rglob("*") if model_dir.exists() else []):
            if path.is_file() and path.suffix.lower() in {".log", ".txt"}:
                hits = text_hits(path)
                if hits:
                    model_timeout_hits += hits
                    all_timeout_files.append({"file": str(path.relative_to(run_dir)), "hits": hits})
        unique_ids = set(task_ids)
        model_rows.append(
            {
                "model_id": model,
                "result_files": len(paths),
                "unique_task_ids": len(unique_ids),
                "duplicate_task_ids": len(task_ids) - len(unique_ids),
                "missing_task_count": max(0, expected - len(unique_ids)),
                "status_counts": dict(status_counts),
                "timeout_like_hits": model_timeout_hits,
                "timeout_task_ids": sorted(timeout_task_ids),
            }
        )
    result = {
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "expected_tasks_per_model": expected,
        "models": model_rows,
        "timeout_like_log_files": all_timeout_files,
        "all_models_present": all(row["result_files"] > 0 for row in model_rows),
        "all_models_have_expected_results": all(
            row["result_files"] == expected and row["unique_task_ids"] == expected and row["duplicate_task_ids"] == 0
            for row in model_rows
        ),
        "any_timeout_like_hits": any(row["timeout_like_hits"] > 0 for row in model_rows) or bool(all_timeout_files),
    }
    if write:
        (run_dir / "timeout_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", action="append", type=Path, default=[])
    parser.add_argument("--benchmark-root", type=Path)
    args = parser.parse_args()
    dirs = [path.resolve() for path in args.run_dir]
    if args.benchmark_root:
        dirs.extend(
            path.parent
            for path in args.benchmark_root.resolve().rglob("run_manifest.json")
            if path.parent not in dirs
        )
    if not dirs:
        raise SystemExit("provide --run-dir or --benchmark-root")
    reports = [inspect_run(path) for path in dirs]
    print(json.dumps(reports, ensure_ascii=False))
    return 0 if all(report["all_models_have_expected_results"] for report in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
