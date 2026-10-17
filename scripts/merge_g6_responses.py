"""Build a deterministic, one-record-per-run G6 response view.

Worker files are append-only and may contain retries from different shard
layouts. A completed response is preferred; when no completed response exists,
the latest terminal failure is retained in the canonical denominator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--responses-dir", type=Path, required=True)
    args = parser.parse_args()

    plan = read_jsonl(args.plan)
    source_files = sorted(
        path for path in args.responses_dir.glob("responses*.jsonl")
        if path.name != args.out.name
    )
    by_run: dict[str, list[dict[str, Any]]] = {}
    for source in source_files:
        for row in read_jsonl(source):
            by_run.setdefault(str(row.get("run_id", "")), []).append(row)

    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    duplicate_completed: dict[str, int] = {}
    terminal_failures: dict[str, str] = {}
    for row in plan:
        run_id = str(row["run_id"])
        completed = [candidate for candidate in by_run.get(run_id, []) if candidate.get("status") == "completed"]
        candidates = by_run.get(run_id, [])
        if completed:
            if len(completed) > 1:
                duplicate_completed[run_id] = len(completed)
            selected.append(completed[-1])
            continue
        if not candidates:
            missing.append(run_id)
            continue
        selected.append(candidates[-1])
        terminal_failures[run_id] = str(candidates[-1].get("status", "unknown"))

    write_jsonl(args.out, selected)
    manifest = {
        "experiment_id": "g6_counterfactual",
        "plan_rows": len(plan),
        "selected_completed_rows": len(selected),
        "selected_terminal_failures": terminal_failures,
        "missing_run_ids": missing,
        "source_files": [str(path) for path in source_files],
        "duplicate_completed_run_ids": duplicate_completed,
        "selection_rule": "plan order; latest completed record, else latest terminal record among sorted append-only source files",
    }
    args.out.with_name("responses_merge_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
