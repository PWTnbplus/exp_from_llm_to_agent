"""Build deterministic canonical G7 state/checkpoint views from append-only workers.

The real-provider runner preserves failed attempts in worker files.  Offline
scoring accepts terminal provider failures as data, so this utility selects the
latest completed record when one exists, otherwise the latest terminal record,
and reports missing IDs instead of silently dropping them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"expected object in {path}:{line_number}")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def merge(
    *,
    expected_ids: list[str],
    source_files: list[Path],
    id_key: str,
    out: Path,
    label: str,
) -> dict[str, Any]:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for source in sorted(source_files, key=lambda item: item.name):
        for row in read_jsonl(source):
            record_id = str(row.get(id_key, ""))
            if record_id:
                by_id.setdefault(record_id, []).append(row)

    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    duplicate_completed: dict[str, int] = {}
    terminal_failures: dict[str, str] = {}
    for record_id in expected_ids:
        candidates = by_id.get(record_id, [])
        completed = [row for row in candidates if row.get("status") == "completed"]
        if completed:
            selected.append(completed[-1])
            if len(completed) > 1:
                duplicate_completed[record_id] = len(completed)
            continue
        if not candidates:
            missing.append(record_id)
            continue
        selected.append(candidates[-1])
        terminal_failures[record_id] = str(candidates[-1].get("status", "unknown"))

    write_jsonl(out, selected)
    return {
        "label": label,
        "expected": len(expected_ids),
        "selected_records": len(selected),
        "selected_completed": len(selected) - len(terminal_failures),
        "selected_terminal_failures": terminal_failures,
        "missing_ids": missing,
        "source_files": [str(path) for path in sorted(source_files, key=lambda item: item.name)],
        "duplicate_completed_ids": duplicate_completed,
        "selection_rule": "expected-id order; latest completed record, else latest terminal record, among stable sorted append-only sources",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--states-dir", type=Path, required=True)
    parser.add_argument("--states-out", type=Path, required=True)
    parser.add_argument("--checkpoints-out", type=Path)
    args = parser.parse_args()

    plan = read_jsonl(args.plan)
    run_ids = [str(row["run_id"]) for row in plan]
    state_sources = sorted(args.states_dir.glob("states*.jsonl"))
    state_manifest = merge(
        expected_ids=run_ids,
        source_files=state_sources,
        id_key="run_id",
        out=args.states_out,
        label="states",
    )

    checkpoint_manifest: dict[str, Any] | None = None
    if args.checkpoints_out is not None:
        checkpoint_ids: list[str] = []
        seen: set[str] = set()
        for row in plan:
            checkpoint_id = str(row["checkpoint_id"])
            if checkpoint_id not in seen:
                seen.add(checkpoint_id)
                checkpoint_ids.append(checkpoint_id)
        checkpoint_sources = sorted(args.states_dir.glob("checkpoints*.jsonl"))
        checkpoint_manifest = merge(
            expected_ids=checkpoint_ids,
            source_files=checkpoint_sources,
            id_key="checkpoint_id",
            out=args.checkpoints_out,
            label="checkpoints",
        )

    manifest = {
        "experiment_id": "g7_failure_localization",
        "plan_rows": len(plan),
        "states": state_manifest,
        "checkpoints": checkpoint_manifest,
    }
    manifest_path = args.states_out.with_name("g7_merge_manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    complete = not state_manifest["missing_ids"] and (
        checkpoint_manifest is None or not checkpoint_manifest["missing_ids"]
    )
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
